"""
Semi-Active Executor — Runs Skills (playbooks) on-demand or triggered by passive mode.

This is the engine that executes Skill sequences using:
  - Vision (screen capture + LLM analysis) for guided mode
  - HID (keyboard/mouse) for target machine interaction
  - SSH for fast command execution
  - Safety checks at every step
"""

import asyncio
import time
import logging
from typing import Optional, Callable, Awaitable

from .models import Task, TaskState, ScreenState, TaskStatus
from .context import ExecutionContext
from ..action.driver import ActionDriver, Action, ActionResult

logger = logging.getLogger("cortex.executor")


class SemiActiveExecutor:
    """
    Executes Skills in the semi-active or manual mode.

    Both modes use the same execution engine — the difference is
    who triggers execution:
      - Manual mode: only user/API triggers
      - Semi-active mode: also triggered by passive monitor
    """

    def __init__(
        self,
        action_driver: ActionDriver,
        vision_backend=None,
        safety_guard=None,
        skill_store=None,
    ):
        self.action = action_driver
        self.vision = vision_backend
        self.guard = safety_guard
        self.skill_store = skill_store

        # Current execution
        self._current_task: Optional[Task] = None
        self._current_context: Optional[ExecutionContext] = None
        self._execution_task: Optional[asyncio.Task] = None
        self._abort_event = asyncio.Event()

        # Task history
        self.task_history: list[Task] = []

        # WebSocket callbacks for real-time updates
        self._ws_callbacks: list[Callable] = []

    # ── Task Execution ──────────────────────────────────────────

    async def run_skill(self, skill_name: str, params: dict = None) -> TaskStatus:
        """
        Execute a skill by name. Main entry point for both manual and triggered execution.

        Returns TaskStatus when complete (or failed/aborted).
        """
        if self._current_task and self._current_task.state == TaskState.RUNNING:
            raise RuntimeError(f"Task already running: {self._current_task.task_id}")

        # Load skill
        if self.skill_store is None:
            raise RuntimeError("No skill store configured")

        skill = self.skill_store.get_skill(skill_name)
        if skill is None:
            raise ValueError(f"Skill not found: {skill_name}")

        # Create task
        task = Task(skill_name=skill_name, params=params or {}, mode=skill.get("mode", "guided"))
        task.state = TaskState.RUNNING
        task.started_at = time.time()
        self._current_task = task
        self._abort_event.clear()

        # Create context
        ctx = ExecutionContext(task=task)
        self._current_context = ctx

        logger.info(f"Starting task {task.task_id}: skill={skill_name}, params={params}")
        await self._notify_ws({"type": "task_start", "task_id": task.task_id, "skill": skill_name})

        try:
            mode = skill.get("mode", "guided")

            if mode == "scripted":
                await self._run_scripted(skill, ctx)
            elif mode == "guided":
                await self._run_guided(skill, ctx)
            else:
                raise ValueError(f"Unknown skill mode: {mode}")

            if not ctx.is_complete:
                ctx.mark_complete()
            logger.info(f"Task {task.task_id} completed successfully")

        except asyncio.CancelledError:
            ctx.mark_aborted()
            logger.info(f"Task {task.task_id} aborted")
        except Exception as e:
            ctx.mark_failed(str(e))
            logger.error(f"Task {task.task_id} failed: {e}")

        # Save to history
        self.task_history.append(task)
        if len(self.task_history) > 50:
            self.task_history = self.task_history[-50:]

        status = ctx.task.to_status(ctx.progress, ctx.current_step, ctx.current_checkpoint)
        await self._notify_ws({"type": "task_end", "task_id": task.task_id, "status": status.model_dump()})

        self._current_task = None
        self._current_context = None
        return status

    async def run_skill_async(self, skill_name: str, params: dict = None) -> str:
        """Start a skill execution in background. Returns task_id."""
        if self._current_task and self._current_task.state == TaskState.RUNNING:
            raise RuntimeError(f"Task already running: {self._current_task.task_id}")

        task = Task(skill_name=skill_name, params=params or {})
        self._execution_task = asyncio.create_task(self.run_skill(skill_name, params))
        return task.task_id

    # ── Scripted Execution ──────────────────────────────────────

    async def _run_scripted(self, skill: dict, ctx: ExecutionContext):
        """Execute a scripted skill (fixed steps)."""
        steps = skill.get("steps", [])
        total = len(steps)

        for i, step in enumerate(steps):
            if self._abort_event.is_set():
                ctx.mark_aborted()
                return

            while ctx.is_paused:
                await asyncio.sleep(0.5)

            step_id = step.get("id", f"step_{i}")
            action_def = step.get("action", {})
            wait_time = step.get("wait", 0.5)
            expect = step.get("expect")
            retry = int(step.get("retry", 1))
            retry_delay = step.get("retry_delay", 1)

            # Substitute parameters
            action_def = self._substitute_params(action_def, ctx.task.params)

            logger.info(f"Step {i+1}/{total}: {step_id}")

            for attempt in range(retry):
                # Safety check
                if self.guard:
                    screen = ScreenState(type="unknown")
                    safety = await self.guard.check(screen, ctx)
                    if safety.get("abort", False):
                        ctx.mark_failed(f"Safety abort: {safety.get('reason')}")
                        return

                # Execute action
                action = Action(**action_def)
                result = await self.action.execute(action)

                # Record step
                ctx.record_step(
                    screen_state=None,
                    action_type=action.type,
                    action_detail=str(action_def),
                    action_result=str(result.output) if result.output else str(result.success),
                    channel="ssh" if result.note != "via_hid" and action.type == "shell" else "hid",
                )

                # Wait
                if wait_time:
                    await asyncio.sleep(wait_time)

                # Verify expectation
                if expect and result.output:
                    if expect in result.output:
                        break  # Success
                    elif attempt < retry - 1:
                        logger.info(f"Step {step_id} retry {attempt+1}/{retry}")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        ctx.mark_failed(f"Step {step_id} failed: expected '{expect}', got '{result.output}'")
                        return
                else:
                    break  # No expectation or no output to verify

            ctx.update_progress((i + 1) / total)
            await self._notify_ws({
                "type": "step",
                "task_id": ctx.task.task_id,
                "step": i + 1,
                "total": total,
                "step_id": step_id,
                "progress": ctx.progress,
            })

    # ── Guided Execution ────────────────────────────────────────

    async def _run_guided(self, skill: dict, ctx: ExecutionContext):
        """
        Execute a guided skill (LLM-driven).
        The Vision API analyzes the screen and decides next actions.
        """
        if self.vision is None:
            raise RuntimeError("Guided mode requires a vision backend")

        goal = skill.get("goal", "")
        goal = self._substitute_params_str(goal, ctx.task.params)
        checkpoints = skill.get("checkpoints", [])
        safety_cfg = skill.get("safety", {})
        max_steps = safety_cfg.get("max_steps", 100)
        max_duration = safety_cfg.get("max_duration", 300)
        recovery = skill.get("recovery", {})

        logger.info(f"Guided execution — Goal: {goal[:100]}...")

        while not ctx.is_complete:
            if self._abort_event.is_set():
                ctx.mark_aborted()
                return

            while ctx.is_paused:
                await asyncio.sleep(0.5)

            # Safety limits
            if ctx.current_step >= max_steps:
                ctx.mark_failed(f"Max steps exceeded ({max_steps})")
                return
            if ctx.elapsed > max_duration:
                ctx.mark_failed(f"Timeout ({max_duration}s)")
                return

            # Loop detection
            if ctx.detect_loop(window=5):
                if recovery.get("on_stuck"):
                    logger.warning(f"Loop detected, trying recovery: {recovery['on_stuck']}")
                    # Simple recovery: press Escape
                    await self.action.execute(Action(type="key_press", key="Escape"))
                    await asyncio.sleep(1)
                else:
                    ctx.mark_failed("Agent stuck in loop")
                    return

            # 1. Capture screen
            try:
                frame = await self.vision.capture()
                screen_state = await self.vision.analyze(frame, ctx, goal, checkpoints)
            except Exception as e:
                logger.error(f"Vision analysis failed: {e}")
                await asyncio.sleep(2)
                continue

            # 2. Check for completion
            if screen_state.type == "task_complete":
                ctx.mark_complete()
                return

            # 3. Safety check
            if self.guard:
                safety = await self.guard.check(screen_state, ctx)
                if safety.get("abort", False):
                    ctx.mark_failed(f"Safety abort: {safety.get('reason')}")
                    return

            # 4. Decide + Act (from vision analysis)
            next_action = screen_state.raw_response  # Vision backend returns action recommendation
            if next_action and isinstance(next_action, dict):
                action_data = next_action.get("next_action", {})
                if action_data.get("type") == "done":
                    ctx.mark_complete()
                    return

                action = Action(**action_data)
                result = await self.action.execute(action)

                ctx.record_step(
                    screen_state=screen_state,
                    action_type=action.type,
                    action_detail=str(action_data),
                    action_result=str(result.output) if result.output else "",
                )

            # 5. Update checkpoint
            if hasattr(screen_state, 'description'):
                for cp in checkpoints:
                    if cp.get("name") and cp["name"] not in ctx.checkpoints_reached:
                        # Simple heuristic: if description mentions checkpoint
                        if cp.get("visual_hint", "").lower() in screen_state.description.lower():
                            ctx.reach_checkpoint(cp["name"])

            # 6. Progress
            if checkpoints:
                ctx.update_progress(len(ctx.checkpoints_reached) / len(checkpoints))

            await self._notify_ws({
                "type": "step",
                "task_id": ctx.task.task_id,
                "step": ctx.current_step,
                "screen_state": screen_state.type,
                "progress": ctx.progress,
                "checkpoint": ctx.current_checkpoint,
            })

            # Wait for screen to stabilize
            await asyncio.sleep(1)

    # ── Task Control ────────────────────────────────────────────

    def abort_current(self):
        """Abort the currently running task."""
        self._abort_event.set()
        if self._execution_task:
            self._execution_task.cancel()

    def pause_current(self):
        """Pause the currently running task."""
        if self._current_context:
            self._current_context.pause()

    def resume_current(self):
        """Resume the currently paused task."""
        if self._current_context:
            self._current_context.resume()

    # ── Status ──────────────────────────────────────────────────

    def get_current_task(self) -> Optional[TaskStatus]:
        """Get current task status."""
        if self._current_context:
            ctx = self._current_context
            return ctx.task.to_status(ctx.progress, ctx.current_step, ctx.current_checkpoint)
        return None

    def get_task_history(self, n: int = 10) -> list[dict]:
        """Get recent task history."""
        return [
            {
                "task_id": t.task_id,
                "skill": t.skill_name,
                "state": t.state.value,
                "error": t.error,
                "result": t.result,
            }
            for t in self.task_history[-n:]
        ]

    # ── Helpers ─────────────────────────────────────────────────

    def _substitute_params(self, obj: dict, params: dict) -> dict:
        """Substitute {param} placeholders in action definitions."""
        result = {}
        for k, v in obj.items():
            if isinstance(v, str):
                result[k] = self._substitute_params_str(v, params)
            elif isinstance(v, dict):
                result[k] = self._substitute_params(v, params)
            else:
                result[k] = v
        return result

    def _substitute_params_str(self, text: str, params: dict) -> str:
        """Substitute {param} in a string."""
        for key, value in params.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text

    # ── WebSocket Notifications ─────────────────────────────────

    def add_ws_callback(self, callback: Callable):
        self._ws_callbacks.append(callback)

    def remove_ws_callback(self, callback: Callable):
        if callback in self._ws_callbacks:
            self._ws_callbacks.remove(callback)

    async def _notify_ws(self, data: dict):
        """Notify all WebSocket listeners."""
        for cb in self._ws_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(data)
                else:
                    cb(data)
            except Exception as e:
                logger.debug(f"WS callback error: {e}")
