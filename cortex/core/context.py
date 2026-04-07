"""
Execution Context — Tracks state during task execution.
"""

import time
import logging
from typing import Optional
from .models import Task, TaskState, StepRecord, ScreenState

logger = logging.getLogger("cortex.context")


class ExecutionContext:
    """
    Tracks all state during the execution of a single task.

    Provides:
      - Step history recording
      - Progress tracking
      - Loop detection
      - Checkpoint management
      - Convenience accessors for the executor
    """

    def __init__(self, task: Task):
        self.task = task
        self.history: list[StepRecord] = []
        self.progress: float = 0.0
        self.current_step: int = 0
        self.current_checkpoint: Optional[str] = None
        self.checkpoints_reached: set[str] = set()
        self._start_time: float = time.time()
        self._is_complete: bool = False
        self._is_paused: bool = False

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def elapsed(self) -> float:
        """Seconds since execution started."""
        return time.time() - self._start_time

    def mark_complete(self, result: dict = None):
        """Mark task as completed."""
        self._is_complete = True
        self.progress = 1.0
        self.task.state = TaskState.COMPLETED
        self.task.completed_at = time.time()
        self.task.result = result

    def mark_failed(self, error: str):
        """Mark task as failed."""
        self._is_complete = True
        self.task.state = TaskState.FAILED
        self.task.completed_at = time.time()
        self.task.error = error

    def mark_aborted(self):
        """Mark task as aborted by user."""
        self._is_complete = True
        self.task.state = TaskState.ABORTED
        self.task.completed_at = time.time()
        self.task.error = "Aborted by user"

    def pause(self):
        self._is_paused = True
        self.task.state = TaskState.PAUSED

    def resume(self):
        self._is_paused = False
        self.task.state = TaskState.RUNNING

    def record_step(
        self,
        screen_state: Optional[ScreenState],
        action_type: str,
        action_detail: str,
        action_result: str,
        channel: str = "hid",
        screenshot_path: str = None,
    ):
        """Record a step in execution history."""
        step = StepRecord(
            step_number=self.current_step,
            timestamp=time.time(),
            screen_state=screen_state,
            action_type=action_type,
            action_detail=action_detail,
            action_result=action_result,
            channel_used=channel,
            screenshot_path=screenshot_path,
        )
        self.history.append(step)
        self.current_step += 1

    def update_progress(self, progress: float):
        """Update progress (0.0 - 1.0)."""
        self.progress = max(0.0, min(1.0, progress))

    def reach_checkpoint(self, name: str):
        """Mark a checkpoint as reached."""
        self.current_checkpoint = name
        self.checkpoints_reached.add(name)
        logger.info(f"Checkpoint reached: {name}")

    def has_reached(self, checkpoint: str) -> bool:
        """Whether a checkpoint has been reached."""
        return checkpoint in self.checkpoints_reached

    def detect_loop(self, window: int = 5) -> bool:
        """
        Detect if the agent is stuck in a loop.
        Checks if the last `window` actions are identical.
        """
        if len(self.history) < window:
            return False

        recent = self.history[-window:]
        action_types = [s.action_type for s in recent]
        action_details = [s.action_detail for s in recent]

        # All same action type AND same detail = loop
        if len(set(action_types)) == 1 and len(set(action_details)) == 1:
            logger.warning(f"Loop detected: {action_types[0]}({action_details[0]}) repeated {window} times")
            return True

        return False

    def get_recent_history(self, n: int = 10) -> list[dict]:
        """Get recent history as serializable dicts."""
        return [
            {
                "step": s.step_number,
                "action": f"{s.action_type}: {s.action_detail}",
                "result": s.action_result,
                "channel": s.channel_used,
            }
            for s in self.history[-n:]
        ]
