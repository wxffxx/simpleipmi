"""
Agent API Routes — FastAPI Router for the Cortex Agent framework.

Provides REST + WebSocket endpoints that any Host can mount via:
    app.include_router(create_agent_router(...), prefix="/api/agent")
"""

import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from pydantic import BaseModel

from ..core.models import AgentMode, AgentStatus, TaskRequest
from ..core.passive import PassiveMonitor
from ..core.executor import SemiActiveExecutor
from ..channels.ssh import SSHChannelManager
from ..action.driver import ActionDriver
from ..action.adapters import HIDAdapterInterface, VideoAdapterInterface, GPIOAdapterInterface
from ..vision.local_backend import LocalVisionBackend
from ..vision.api_backend import APIVisionBackend
from ..skills.store import SkillStore
from ..skills.recorder import SkillRecorder
from ..safety.guard import SafetyGuard

logger = logging.getLogger("cortex.api")


class AgentInstance:
    """
    Central agent instance that wires everything together.
    Created by create_agent_router() and shared across all endpoints.
    """

    def __init__(
        self,
        hid_adapter: HIDAdapterInterface,
        video_adapter: VideoAdapterInterface,
        gpio_adapter: GPIOAdapterInterface,
        config: dict,
    ):
        self.config = config
        self.mode = AgentMode(config.get("mode", "manual"))
        self.start_time = time.time()

        # SSH Channel
        target_cfg = config.get("target", {})
        ssh_cfg = target_cfg.get("ssh", {})
        ssh_cfg["ip"] = target_cfg.get("ip", "")
        self.ssh = SSHChannelManager(ssh_cfg)

        # Action Driver
        self.action_driver = ActionDriver(hid_adapter, gpio_adapter, self.ssh)

        # Vision
        vision_cfg = config.get("vision", {})
        self.local_vision = LocalVisionBackend(video_adapter)
        if vision_cfg.get("api_key"):
            self.vision = APIVisionBackend(video_adapter, vision_cfg)
        else:
            self.vision = self.local_vision

        # Safety
        safety_cfg = config.get("safety", {})
        self.guard = SafetyGuard(safety_cfg)

        # Skill Store
        skills_dir = config.get("skills_dir", "./skill_library")
        self.skill_store = SkillStore(library_dir=skills_dir)
        self.skill_store.load_all()

        # Executor
        self.executor = SemiActiveExecutor(
            action_driver=self.action_driver,
            vision_backend=self.vision,
            safety_guard=self.guard,
            skill_store=self.skill_store,
        )

        # Passive Monitor
        passive_cfg = config.get("passive", {})
        self.passive = PassiveMonitor(
            vision_adapter=video_adapter,
            ssh_manager=self.ssh,
            action_driver=self.action_driver,
            config=passive_cfg,
        )
        self.passive.set_skill_runner(self._run_skill_from_trigger)

        # Recorder
        self.recorder = SkillRecorder(vision_adapter=video_adapter)

    async def startup(self):
        """Initialize on server startup."""
        # Try SSH connection
        target_ip = self.config.get("target", {}).get("ip", "")
        if target_ip:
            connected = await self.ssh.connect(timeout=5)
            if connected:
                logger.info(f"SSH connected to target: {target_ip}")
            else:
                logger.info(f"SSH not available (target: {target_ip})")

        # Start passive monitor if mode requires it
        if self.mode in (AgentMode.PASSIVE, AgentMode.SEMI_ACTIVE):
            await self.passive.start()

    async def shutdown(self):
        """Cleanup on server shutdown."""
        await self.passive.stop()
        await self.ssh.close()
        if hasattr(self.vision, "close"):
            await self.vision.close()

    async def _run_skill_from_trigger(self, skill_name: str, params: dict):
        """Called by passive monitor to run a recovery skill."""
        try:
            await self.executor.run_skill(skill_name, params)
        except Exception as e:
            logger.error(f"Trigger skill execution failed: {e}")

    def get_status(self) -> AgentStatus:
        return AgentStatus(
            mode=self.mode,
            passive_running=self.passive.running,
            current_task=self.executor.get_current_task(),
            ssh_connected=self.ssh.has_shell,
            ssh_target=self.ssh.get_status()["target"],
            services_monitored=len(self.passive.services),
            recent_triggers=self.passive.trigger_history[-5:],
            uptime=time.time() - self.start_time,
        )


# ═══════════════════════════════════════════════════════════════
# Router Factory
# ═══════════════════════════════════════════════════════════════

def create_agent_router(
    hid_adapter: HIDAdapterInterface,
    video_adapter: VideoAdapterInterface,
    gpio_adapter: GPIOAdapterInterface,
    config: dict,
) -> APIRouter:
    """Create a FastAPI Router with all Agent endpoints."""

    router = APIRouter(tags=["Agent (Cortex)"])
    agent = AgentInstance(hid_adapter, video_adapter, gpio_adapter, config)

    # ── Lifecycle Events ────────────────────────────────────────

    @router.on_event("startup")
    async def on_startup():
        await agent.startup()

    @router.on_event("shutdown")
    async def on_shutdown():
        await agent.shutdown()

    # ── Status ──────────────────────────────────────────────────

    @router.get("/status")
    async def get_status():
        """Get overall agent status."""
        return agent.get_status().model_dump()

    # ── Mode Control ────────────────────────────────────────────

    class ModeRequest(BaseModel):
        mode: str  # "manual" | "passive" | "semi_active"

    @router.post("/mode")
    async def set_mode(req: ModeRequest):
        """Switch agent operating mode."""
        try:
            new_mode = AgentMode(req.mode)
        except ValueError:
            raise HTTPException(400, f"Invalid mode: {req.mode}")

        old_mode = agent.mode
        agent.mode = new_mode

        # Start/stop passive monitor based on mode
        if new_mode in (AgentMode.PASSIVE, AgentMode.SEMI_ACTIVE):
            if not agent.passive.running:
                await agent.passive.start()
        else:
            if agent.passive.running:
                await agent.passive.stop()

        return {"old_mode": old_mode.value, "new_mode": new_mode.value}

    # ── Passive Monitor ─────────────────────────────────────────

    @router.get("/passive/status")
    async def passive_status():
        """Get passive monitor status and recent triggers."""
        return agent.passive.get_status()

    @router.post("/passive/start")
    async def passive_start():
        """Manually start passive monitoring."""
        await agent.passive.start()
        return {"status": "started"}

    @router.post("/passive/stop")
    async def passive_stop():
        """Stop passive monitoring."""
        await agent.passive.stop()
        return {"status": "stopped"}

    # ── Task Execution ──────────────────────────────────────────

    @router.post("/task")
    async def run_task(req: TaskRequest):
        """Execute a skill. Returns when complete."""
        try:
            result = await agent.executor.run_skill(req.skill_name, req.params)
            return result.model_dump()
        except ValueError as e:
            raise HTTPException(404, str(e))
        except RuntimeError as e:
            raise HTTPException(409, str(e))

    @router.get("/task/current")
    async def current_task():
        """Get currently running task status."""
        task = agent.executor.get_current_task()
        if task:
            return task.model_dump()
        return {"status": "idle"}

    @router.post("/task/abort")
    async def abort_task():
        """Abort the currently running task."""
        agent.executor.abort_current()
        return {"status": "aborting"}

    @router.post("/task/pause")
    async def pause_task():
        """Pause the currently running task."""
        agent.executor.pause_current()
        return {"status": "paused"}

    @router.post("/task/resume")
    async def resume_task():
        """Resume the currently paused task."""
        agent.executor.resume_current()
        return {"status": "resumed"}

    @router.get("/task/history")
    async def task_history():
        """Get recent task execution history."""
        return {"tasks": agent.executor.get_task_history()}

    # ── Skills ──────────────────────────────────────────────────

    @router.get("/skills")
    async def list_skills(tag: str = None):
        """List all available skills."""
        tags = [tag] if tag else None
        return {"skills": agent.skill_store.list_skills(tags)}

    @router.get("/skills/{name}")
    async def get_skill(name: str):
        """Get skill details."""
        skill = agent.skill_store.get_skill(name)
        if not skill:
            raise HTTPException(404, f"Skill not found: {name}")
        return skill.to_dict()

    @router.get("/skills/{name}/export")
    async def export_skill(name: str):
        """Export a skill as YAML."""
        content = agent.skill_store.export_skill(name)
        if content is None:
            raise HTTPException(404, f"Skill not found: {name}")
        return {"name": name, "yaml": content}

    @router.post("/skills/import")
    async def import_skill(file: UploadFile = File(...)):
        """Import a skill from a YAML file."""
        if not file.filename.endswith((".yaml", ".yml")):
            raise HTTPException(400, "Only YAML files accepted")

        content = await file.read()
        content_str = content.decode("utf-8")

        # Save to custom directory
        import tempfile, os, yaml as _yaml
        tmp = os.path.join(tempfile.gettempdir(), file.filename)
        with open(tmp, "w") as f:
            f.write(content_str)

        try:
            skill = agent.skill_store.import_skill(tmp, category="custom")
            return {"imported": skill.name, "path": skill.source_path}
        except Exception as e:
            raise HTTPException(400, f"Import failed: {e}")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    class SkillCreateRequest(BaseModel):
        name: str
        content: str
        category: str = "custom"

    @router.post("/skills")
    async def create_skill(req: SkillCreateRequest):
        """Create a new skill from YAML content."""
        path = agent.skill_store.save_skill(req.name, req.content, req.category)
        return {"name": req.name, "path": path}

    @router.delete("/skills/{name}")
    async def delete_skill(name: str):
        """Delete a skill."""
        if agent.skill_store.delete_skill(name):
            return {"deleted": name}
        raise HTTPException(404, f"Skill not found or is builtin: {name}")

    # ── SSH Channel ─────────────────────────────────────────────

    @router.get("/ssh/status")
    async def ssh_status():
        """Get SSH connection status."""
        return agent.ssh.get_status()

    class SSHConnectRequest(BaseModel):
        ip: Optional[str] = None
        port: int = 22
        username: str = "root"
        password: Optional[str] = None

    @router.post("/ssh/connect")
    async def ssh_connect(req: SSHConnectRequest = None):
        """Connect to target machine via SSH."""
        if req and req.ip:
            agent.ssh.target_ip = req.ip
            agent.ssh.port = req.port
            agent.ssh.username = req.username
            if req.password:
                agent.ssh.password = req.password

        success = await agent.ssh.connect()
        if success:
            return {"status": "connected", **agent.ssh.get_status()}
        raise HTTPException(503, "SSH connection failed")

    @router.post("/ssh/disconnect")
    async def ssh_disconnect():
        """Disconnect SSH."""
        await agent.ssh.close()
        return {"status": "disconnected"}

    class SSHCommandRequest(BaseModel):
        command: str
        timeout: int = 30

    @router.post("/ssh/exec")
    async def ssh_exec(req: SSHCommandRequest):
        """Execute a command on the target machine via SSH."""
        if not agent.ssh.has_shell:
            raise HTTPException(503, "SSH not connected")
        try:
            output = await agent.ssh.run(req.command, timeout=req.timeout)
            return {"output": output}
        except Exception as e:
            raise HTTPException(500, str(e))

    # ── Recording ───────────────────────────────────────────────

    class RecordRequest(BaseModel):
        name: str

    @router.post("/record/start")
    async def record_start(req: RecordRequest):
        """Start recording operations."""
        agent.recorder.start(req.name)
        return {"status": "recording", "name": req.name}

    @router.post("/record/stop")
    async def record_stop():
        """Stop recording and return the generated skill."""
        skill_data = await agent.recorder.stop()

        # Auto-save to skill store
        import yaml as _yaml
        name = skill_data.get("skill", {}).get("name", "recorded")
        content = _yaml.dump(skill_data, default_flow_style=False, allow_unicode=True)
        agent.skill_store.save_skill(name, content, category="custom")

        return {"skill": skill_data, "saved_as": name}

    @router.get("/record/status")
    async def record_status():
        """Get recorder status."""
        return agent.recorder.get_status()

    # ── WebSocket ───────────────────────────────────────────────

    @router.websocket("/ws")
    async def agent_websocket(websocket: WebSocket):
        """Real-time agent events (task progress, triggers, screenshots)."""
        await websocket.accept()
        logger.info("Agent WebSocket connected")

        async def ws_callback(data: dict):
            try:
                await websocket.send_json(data)
            except Exception:
                pass

        agent.executor.add_ws_callback(ws_callback)

        try:
            while True:
                msg = await websocket.receive_json()
                # Handle client messages (confirm, override, etc.)
                msg_type = msg.get("type")
                if msg_type == "confirm":
                    # TODO: wire to safety guard confirmation
                    pass
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            logger.info("Agent WebSocket disconnected")
        finally:
            agent.executor.remove_ws_callback(ws_callback)

    return router, agent
