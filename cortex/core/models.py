"""
Core Data Models — Pydantic models for tasks, actions, and execution state.
"""

import time
import uuid
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ── Agent Modes ─────────────────────────────────────────────────

class AgentMode(str, Enum):
    MANUAL = "manual"           # Human-triggered only, no background monitoring
    PASSIVE = "passive"         # Watchdog: monitor + auto-recover on anomaly
    SEMI_ACTIVE = "semi_active" # Passive + scheduled/conditional skill execution


# ── Task Models ─────────────────────────────────────────────────

class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class TaskRequest(BaseModel):
    """API request to create a task."""
    skill_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    mode: str = "guided"  # "guided" | "scripted"


class TaskStatus(BaseModel):
    """Current status of a running/completed task."""
    task_id: str
    skill_name: str
    state: TaskState
    progress: float = 0.0       # 0.0 - 1.0
    current_step: int = 0
    total_steps: Optional[int] = None
    current_checkpoint: Optional[str] = None
    started_at: float
    elapsed: float = 0.0
    error: Optional[str] = None
    result: Optional[dict] = None


class Task:
    """Internal task representation."""

    def __init__(self, skill_name: str, params: dict = None, mode: str = "guided"):
        self.task_id = str(uuid.uuid4())[:8]
        self.skill_name = skill_name
        self.params = params or {}
        self.mode = mode
        self.state = TaskState.PENDING
        self.started_at = 0.0
        self.completed_at = 0.0
        self.error: Optional[str] = None
        self.result: Optional[dict] = None

    def to_status(self, progress: float = 0.0, step: int = 0, checkpoint: str = None) -> TaskStatus:
        elapsed = time.time() - self.started_at if self.started_at else 0
        return TaskStatus(
            task_id=self.task_id,
            skill_name=self.skill_name,
            state=self.state,
            progress=progress,
            current_step=step,
            current_checkpoint=checkpoint,
            started_at=self.started_at,
            elapsed=elapsed,
            error=self.error,
            result=self.result,
        )


# ── Screen State ────────────────────────────────────────────────

class ScreenState(BaseModel):
    """Structured representation of what's on the target machine's screen."""
    type: str = "unknown"         # "off", "bios", "os_desktop", "os_login", "error", "unknown"
    description: str = ""         # Human-readable description
    error: Optional[str] = None   # Error type if screen.type == "error"
    elements: list[str] = Field(default_factory=list)  # Detected UI elements
    raw_response: Optional[str] = None  # Raw LLM response (for debugging)

    @classmethod
    def from_api_response(cls, response: dict) -> "ScreenState":
        """Parse Vision API response into ScreenState."""
        return cls(
            type=response.get("screen_state", "unknown"),
            description=response.get("observations", ""),
            error=response.get("error"),
            elements=response.get("elements", []),
            raw_response=str(response),
        )


# ── Execution Step ──────────────────────────────────────────────

class StepRecord(BaseModel):
    """Record of a single step in execution history."""
    step_number: int
    timestamp: float
    screen_state: Optional[ScreenState] = None
    action_type: str = ""
    action_detail: str = ""
    action_result: str = ""
    channel_used: str = "hid"     # "hid" | "ssh"
    screenshot_path: Optional[str] = None  # Path to saved screenshot


# ── Service Monitor Models ──────────────────────────────────────

class ServiceType(str, Enum):
    SYSTEMD = "systemd"
    PROCESS = "process"
    DOCKER = "docker"


class ServiceConfig(BaseModel):
    """Configuration for a monitored service."""
    name: str
    type: ServiceType = ServiceType.SYSTEMD
    unit: Optional[str] = None          # systemd unit name
    process: Optional[str] = None       # process name for pgrep
    match: Optional[str] = None         # process arg match string
    container: Optional[str] = None     # docker container name
    check_port: Optional[int] = None    # TCP port to verify
    check_url: Optional[str] = None     # HTTP URL to verify
    on_down: str = "notify"             # "notify" | "restart" | "run_skill:<name>"
    max_restarts: int = 3
    cooldown: int = 60                  # Seconds between restart attempts
    on_max_restarts: str = "notify"     # What to do after max restarts exhausted

    # Runtime state (not from config)
    restart_count: int = 0
    last_restart: float = 0.0
    last_status: Optional[bool] = None


# ── Trigger Models ──────────────────────────────────────────────

class TriggerType(str, Enum):
    BLACK_SCREEN = "black_screen"
    FROZEN_SCREEN = "frozen_screen"
    BLUE_TINT = "blue_tint"
    SSH_CHECK = "ssh_check"
    SERVICE = "service"


class TriggerEvent(BaseModel):
    """An event fired when a trigger condition is met."""
    trigger_name: str
    trigger_type: TriggerType
    timestamp: float = Field(default_factory=time.time)
    description: str = ""
    action: str = ""
    resolved: bool = False


# ── Agent Status ────────────────────────────────────────────────

class AgentStatus(BaseModel):
    """Overall agent status for API responses."""
    mode: AgentMode
    passive_running: bool = False
    current_task: Optional[TaskStatus] = None
    ssh_connected: bool = False
    ssh_target: str = ""
    services_monitored: int = 0
    recent_triggers: list[TriggerEvent] = Field(default_factory=list)
    uptime: float = 0.0
