"""
Cortex Test Server — Mac 本地测试用

使用 Mock HID/Video/GPIO + 真实 SSH 连接到 192.168.1.98 (WSL)

启动: python test_server.py
访问: http://localhost:8090/docs (Swagger UI)
"""

import sys
import os
import asyncio
import logging
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager

from cortex.api.routes import create_agent_router
from cortex.action.adapters import MockHIDAdapter, MockVideoAdapter, MockGPIOAdapter

# ── Config persistence ──────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "cortex_config.json")

def load_saved_config():
    """Load config from persistent file if it exists"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_config_to_file(config):
    """Save config to persistent file"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# ── Config ──────────────────────────────────────────────────────
CONFIG = {
    "mode": "manual",  # Start in manual mode, switch via API
    "target": {
        "ip": "192.168.1.98",
        "ssh": {
            "port": 22,
            "username": "wxffxx",
            "key_file": os.path.expanduser("~/.ssh/id_ed25519"),
            # If key auth fails, run: ssh-copy-id wxffxx@192.168.1.98
            # Or uncomment and set password:
            "password": "123898",
        },
        "auto_bootstrap": False,
    },
    "passive": {
        "poll_interval": 10,
        "services": {
            # Real services running on WSL
            "docker": {
                "type": "systemd",
                "unit": "docker",
                "on_down": "restart",
                "max_restarts": 3,
            },
            "mosquitto": {
                "type": "systemd",
                "unit": "mosquitto",
                "check_port": 1883,
                "on_down": "restart",
                "max_restarts": 3,
            },
            "redis": {
                "type": "systemd",
                "unit": "redis-server",
                "check_port": 6379,
                "on_down": "restart",
                "max_restarts": 2,
            },
        },
        "local_triggers": {
            "black_screen": {"enabled": False},   # No video capture on Mac
            "frozen_screen": {"enabled": False},
        },
        "ssh_triggers": {},
    },
    "vision": {
        "backend": "local",
        # "api_provider": "openai",
        # "api_key": os.environ.get("OPENAI_API_KEY", ""),
        # "model": "gpt-4o",
    },
    "safety": {
        "max_steps": 200,
        "max_duration": 600,
        "require_confirmation": False,  # Auto-approve for testing
    },
    "skills_dir": os.path.join(os.path.dirname(__file__), "cortex", "skill_library"),
}

# ── Logging ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ── App ─────────────────────────────────────────────────────────
agent_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_instance
    logging.info("=" * 50)
    logging.info("Cortex Test Server starting...")
    logging.info(f"Target: {CONFIG['target']['ip']}")
    logging.info("=" * 50)
    await agent_instance.startup()
    yield
    await agent_instance.shutdown()
    logging.info("Cortex Test Server stopped")

app = FastAPI(
    title="Cortex Test Server",
    description="KVM Agent Framework — Mac 本地测试 (Mock HID/Video + Real SSH)",
    version="0.1.0",
    lifespan=lifespan,
)

# Create mock adapters (no real KVM hardware on Mac)
hid = MockHIDAdapter()
video = MockVideoAdapter()
gpio = MockGPIOAdapter()

# Mount Cortex agent
router, agent_instance = create_agent_router(
    hid_adapter=hid,
    video_adapter=video,
    gpio_adapter=gpio,
    config=CONFIG,
)
app.include_router(router, prefix="/api/agent")


# ── Dashboard ───────────────────────────────────────────────────
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "cortex", "dashboard")

@app.get("/")
async def root():
    return FileResponse(os.path.join(DASHBOARD_DIR, "index.html"))

@app.get("/settings")
async def settings_page():
    return FileResponse(os.path.join(DASHBOARD_DIR, "settings.html"))



# ── Config API ──────────────────────────────────────────────────
@app.get("/api/agent/config")
async def get_config():
    saved = load_saved_config()
    return JSONResponse(saved or CONFIG)

@app.post("/api/agent/config")
async def update_config(request: Request):
    body = await request.json()
    save_config_to_file(body)
    return JSONResponse({"status": "ok", "message": "Config saved"})


# ── Conversations API ───────────────────────────────────────────
CONVERSATIONS_FILE = os.path.join(os.path.dirname(__file__), "cortex_conversations.json")

def _load_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _save_conversations(convos):
    with open(CONVERSATIONS_FILE, "w") as f:
        json.dump(convos, f, indent=2, ensure_ascii=False)

@app.get("/api/conversations")
async def list_conversations():
    """List all conversations (without messages for brevity)"""
    convos = _load_conversations()
    # Return summary only (no messages)
    summary = []
    for c in convos:
        summary.append({
            "id": c["id"],
            "title": c.get("title", "新对话"),
            "model": c.get("model", ""),
            "created_at": c.get("created_at", ""),
            "updated_at": c.get("updated_at", ""),
            "message_count": len(c.get("messages", [])),
        })
    return JSONResponse(summary)

@app.post("/api/conversations")
async def create_conversation(request: Request):
    """Create a new conversation"""
    from datetime import datetime
    import uuid

    body = await request.json()
    convos = _load_conversations()

    new_convo = {
        "id": str(uuid.uuid4())[:8],
        "title": body.get("title", "新对话"),
        "model": body.get("model", ""),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [],
    }
    convos.insert(0, new_convo)  # newest first
    _save_conversations(convos)
    return JSONResponse(new_convo)

@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """Get a conversation with all messages"""
    convos = _load_conversations()
    for c in convos:
        if c["id"] == conv_id:
            return JSONResponse(c)
    return JSONResponse({"error": "Not found"}, status_code=404)

@app.post("/api/conversations/{conv_id}/messages")
async def add_message(conv_id: str, request: Request):
    """Add a message to a conversation"""
    from datetime import datetime

    body = await request.json()
    convos = _load_conversations()

    for c in convos:
        if c["id"] == conv_id:
            msg = {
                "role": body.get("role", "user"),
                "content": body.get("content", ""),
                "html": body.get("html", ""),
                "timestamp": datetime.now().isoformat(),
                "cls": body.get("cls", ""),
            }
            c.setdefault("messages", []).append(msg)
            c["updated_at"] = datetime.now().isoformat()
            # Auto-generate title from first user message
            if c.get("title") == "新对话" and msg["role"] == "user" and msg["content"]:
                c["title"] = msg["content"][:30]
            _save_conversations(convos)
            return JSONResponse(msg)

    return JSONResponse({"error": "Not found"}, status_code=404)

@app.patch("/api/conversations/{conv_id}")
async def update_conversation(conv_id: str, request: Request):
    """Update conversation metadata (title, model)"""
    body = await request.json()
    convos = _load_conversations()

    for c in convos:
        if c["id"] == conv_id:
            if "title" in body:
                c["title"] = body["title"]
            if "model" in body:
                c["model"] = body["model"]
            _save_conversations(convos)
            return JSONResponse(c)

    return JSONResponse({"error": "Not found"}, status_code=404)

@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation"""
    convos = _load_conversations()
    convos = [c for c in convos if c["id"] != conv_id]
    _save_conversations(convos)
    return JSONResponse({"status": "ok"})


# ── LLM Models Proxy (avoid CORS) ──────────────────────────────
@app.get("/api/llm/models")
async def proxy_llm_models(provider: str = "gemini", api_key: str = "", endpoint: str = ""):
    """Proxy model list requests to avoid browser CORS issues"""
    import aiohttp

    try:
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    # Check for API error
                    if "error" in data:
                        err_msg = data["error"].get("message", "Unknown error")
                        return JSONResponse({"models": [], "error": err_msg})
                    models = []
                    for m in data.get("models", []):
                        name = m.get("name", "").replace("models/", "")
                        if "generateContent" in str(m.get("supportedGenerationMethods", [])):
                            models.append({
                                "id": name,
                                "name": m.get("displayName", name),
                                "desc": m.get("description", "")[:80],
                            })
                    return JSONResponse({"models": models})

        elif provider == "openai":
            url = endpoint or "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
                    models = [{"id": m["id"], "name": m["id"], "desc": ""} for m in data.get("data", [])]
                    models.sort(key=lambda m: m["id"])
                    return JSONResponse({"models": models})

        elif provider == "ollama":
            url = (endpoint or "http://localhost:11434") + "/api/tags"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    models = [{"id": m["name"], "name": m["name"], "desc": f"{m.get('size', 0) // 1e9:.1f}GB"} for m in data.get("models", [])]
                    return JSONResponse({"models": models})

        elif provider == "anthropic":
            # Anthropic doesn't have a models API, return known models
            return JSONResponse({"models": [
                {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "desc": "Latest balanced model"},
                {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "desc": "Fast and efficient"},
                {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "desc": "Most capable"},
            ]})

        else:
            return JSONResponse({"models": [], "error": f"Unknown provider: {provider}"})

    except Exception as e:
        return JSONResponse({"models": [], "error": str(e)}, status_code=500)


# ── LLM Chat (AI Command Parser) ───────────────────────────────
SYSTEM_PROMPT = """You are Cortex, an AI assistant for server management via SSH.
The user gives natural language commands about managing a Linux server.
Your job is to understand the intent and return the appropriate response.

CRITICAL RULES:
1. You MUST respond with ONLY valid JSON. No markdown, no explanation, no code fences.
2. All commands MUST be single-line. Use && or ; to chain multiple operations.
3. NEVER use heredoc (<<), multi-line strings, or cat with inline content.
4. To create files, use: echo '...' > file  OR  printf '...' > file

You have THREE response types:

## Type 1: ssh — Single command (for simple tasks)
{"type": "ssh", "command": "<single-line command>", "description": "<brief Chinese description>", "dangerous": false}

## Type 2: plan — Multi-step plan (for complex tasks requiring multiple commands)
Use this when the task requires 2+ sequential steps (install, configure, deploy, diagnose, etc.)
{"type": "plan", "goal": "<overall goal in Chinese>", "steps": [
  {"id": 1, "description": "<step description in Chinese>", "command": "<single-line command>", "dangerous": false},
  {"id": 2, "description": "<step description in Chinese>", "command": "<single-line command>", "dangerous": true}
]}

## Type 3: chat — Conversational response (for questions/greetings)
{"type": "chat", "message": "<your helpful response in Chinese>"}

WHEN TO USE plan vs ssh:
- "查看磁盘" → ssh (single command)
- "安装并配置 nginx 反向代理" → plan (install → configure → restart → verify)
- "部署 redis 主从" → plan (install → config master → config slave → test)
- "检查为什么网站打不开" → plan (check nginx → check port → check firewall → check logs)
- "重启某个服务" → ssh (single command)

For dangerous operations (install, restart, stop, reboot, rm, kill, chmod, chown, apt, yum):
Mark the step or command with "dangerous": true

Examples:

User: 查看磁盘使用情况
{"type": "ssh", "command": "df -h | grep -E '^/dev|Filesystem'", "description": "查看磁盘使用情况", "dangerous": false}

User: 安装并启动 redis
{"type": "plan", "goal": "安装并启动 Redis 服务", "steps": [
  {"id": 1, "description": "检查 Redis 是否已安装", "command": "which redis-server && redis-server --version || echo NOT_INSTALLED", "dangerous": false},
  {"id": 2, "description": "安装 Redis", "command": "sudo apt update && sudo apt install -y redis-server", "dangerous": true},
  {"id": 3, "description": "启动 Redis 服务", "command": "sudo systemctl enable redis-server && sudo systemctl start redis-server", "dangerous": true},
  {"id": 4, "description": "验证 Redis 运行状态", "command": "systemctl is-active redis-server && redis-cli ping", "dangerous": false}
]}

User: 你好
{"type": "chat", "message": "你好！我是 Cortex，你的服务器管理助手。你可以用自然语言告诉我你想执行什么操作，比如'查看内存使用'或'安装并配置 nginx'。复杂任务我会自动拆分为多步骤计划。"}
"""

STEP_EVAL_PROMPT = """You are Cortex's plan evaluator. You are given a step that was just executed and its output.
Decide what to do next. Respond with ONLY valid JSON.

Possible actions:
- {{"action": "continue"}} — proceed to next step
- {{"action": "skip", "next_step_id": <id>, "reason": "<Chinese reason>"}} — skip the next step
- {{"action": "modify", "replace_step_id": <id>, "new_command": "<fixed command>", "reason": "<Chinese reason>"}} — modify a future step
- {{"action": "abort", "reason": "<Chinese reason>"}} — stop the plan entirely
- {{"action": "add_step", "after_step_id": <id>, "description": "<Chinese desc>", "command": "<cmd>", "dangerous": false, "reason": "<Chinese reason>"}} — insert an extra step

Context:
Goal: {goal}
Step {step_id}/{total}: {description}
Command: {command}
Output: {output}
Exit success: {success}
Remaining steps: {remaining}

Based on the output, decide what to do next.
"""


def _parse_llm_response(text: str):
    """Robustly parse LLM response text into a structured result dict.
    
    Handles: valid JSON, markdown-wrapped JSON, multi-line commands,
    and malformed JSON via field extraction.
    """
    import re

    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    # Attempt 1: direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: extract type first, then handle per-type
    type_match = re.search(r'"type"\s*:\s*"(\w+)"', text)
    if type_match:
        rtype = type_match.group(1)

        if rtype == "ssh":
            # Extract command: find "command": " then read until the matching close
            # Handle multi-line by finding the field boundaries
            cmd = _extract_json_string_field(text, "command")
            desc = _extract_json_string_field(text, "description")
            danger_match = re.search(r'"dangerous"\s*:\s*(true|false)', text, re.IGNORECASE)

            if cmd:
                # Collapse multi-line command into single line
                # Replace literal newlines with ; (safer than &&)
                cmd = cmd.replace('\n', '; ').replace('\r', '')
                # Clean up multiple semicolons
                cmd = re.sub(r';\s*;', ';', cmd)
                cmd = cmd.strip('; ')
                return {
                    "type": "ssh",
                    "command": cmd,
                    "description": desc or "执行命令",
                    "dangerous": danger_match.group(1).lower() == 'true' if danger_match else False
                }

        if rtype == "chat":
            msg = _extract_json_string_field(text, "message")
            return {
                "type": "chat",
                "message": msg or text
            }

        if rtype == "plan":
            # Plan type: try to extract goal and steps
            goal = _extract_json_string_field(text, "goal")
            # Try to parse steps from the JSON text
            steps_match = re.search(r'"steps"\s*:\s*\[', text)
            if steps_match:
                # Find the matching ]
                bracket_start = steps_match.end() - 1
                depth = 0
                i = bracket_start
                while i < len(text):
                    if text[i] == '[': depth += 1
                    elif text[i] == ']': depth -= 1
                    if depth == 0:
                        steps_json = text[bracket_start:i+1]
                        try:
                            steps = json.loads(steps_json)
                            return {"type": "plan", "goal": goal or "执行计划", "steps": steps}
                        except json.JSONDecodeError:
                            pass
                        break
                    i += 1
            # Couldn't parse steps — fallback to a single ssh command
            cmd = _extract_json_string_field(text, "command")
            if cmd:
                return {"type": "ssh", "command": cmd, "description": goal or "执行命令", "dangerous": False}
            return {"type": "chat", "message": goal or text}

    # Attempt 3: the text itself is the answer (no JSON at all)
    return {"type": "chat", "message": text}


def _extract_json_string_field(text: str, field_name: str) -> str:
    """Extract a string field value from potentially malformed JSON.
    
    Finds "field_name": "..." and extracts the value.
    For multi-line content, uses the next JSON key as boundary.
    """
    import re
    # Find the field start: "field_name" : "
    pattern = f'"{field_name}"\\s*:\\s*"'
    match = re.search(pattern, text)
    if not match:
        return ""
    
    start = match.end()  # Position right after the opening "
    
    # Strategy 1: try clean extraction (escaped-quote aware)
    i = start
    result_chars = []
    while i < len(text):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            result_chars.append(text[i:i+2])
            i += 2
        elif ch == '"':
            break
        else:
            result_chars.append(ch)
            i += 1
    
    clean_result = ''.join(result_chars)
    
    # If clean extraction got a reasonable result (>5 chars for commands), use it
    if len(clean_result) > 5 or field_name != "command":
        return clean_result
    
    # Strategy 2: for short/truncated results, use boundary detection
    # Look for the next field key after our field
    next_fields = ['"description"', '"dangerous"', '"type"', '"message"', '"command"']
    remaining = text[start:]
    
    best_end = len(remaining)
    for nf in next_fields:
        if nf == f'"{field_name}"':
            continue
        idx = remaining.find(nf)
        if idx > 0 and idx < best_end:
            best_end = idx
    
    # Extract everything up to the boundary, then strip trailing ", and whitespace
    raw = remaining[:best_end].rstrip()
    # Remove trailing: ", or "  or ,
    raw = re.sub(r'[",\s]+$', '', raw)
    # Remove leading/trailing quotes if present
    raw = raw.strip('"')
    
    return raw


@app.post("/api/llm/chat")
async def llm_chat(request: Request):
    """Use LLM to parse natural language into SSH commands"""
    import aiohttp

    body = await request.json()
    user_msg = body.get("message", "")

    # Load NLP config from saved config
    saved = load_saved_config() or {}
    nlp_cfg = saved.get("nlp", {})
    provider = nlp_cfg.get("api_provider", "gemini")
    api_key = nlp_cfg.get("api_key", "")
    model = nlp_cfg.get("model", "")

    # Allow per-request model override (from conversation model selector)
    if body.get("model"):
        model = body["model"]

    if not api_key:
        return JSONResponse({"error": "No API key configured. Go to Settings → AI 指令理解."}, status_code=400)

    text = ""
    try:
        if provider == "gemini":
            model = model or "gemini-2.0-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\nUser: " + user_msg}]}
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 2048,
                }
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    if "error" in data:
                        return JSONResponse({"error": data["error"].get("message", "API error")}, status_code=500)
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        elif provider in ("openai", "custom"):
            endpoint = nlp_cfg.get("endpoint", "") or "https://api.openai.com/v1/chat/completions"
            model = model or "gpt-4o"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, headers=headers) as resp:
                    data = await resp.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        elif provider == "anthropic":
            model = model or "claude-sonnet-4-20250514"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "max_tokens": 2048,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_msg}],
            }
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers) as resp:
                    data = await resp.json()
                    text = data.get("content", [{}])[0].get("text", "")

        elif provider == "ollama":
            ollama_url = nlp_cfg.get("ollama_url", "http://localhost:11434")
            model = nlp_cfg.get("ollama_model", model or "llama3.1:8b")
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ],
                "stream": False,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{ollama_url}/api/chat", json=payload) as resp:
                    data = await resp.json()
                    text = data.get("message", {}).get("content", "")

        else:
            return JSONResponse({"error": f"Unsupported provider: {provider}"}, status_code=400)

        # Parse response using robust multi-attempt parser
        result = _parse_llm_response(text)
        return JSONResponse({"result": result})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/llm/step")
async def llm_step_eval(request: Request):
    """ReAct: evaluate a plan step result and decide next action"""
    import aiohttp

    body = await request.json()
    goal = body.get("goal", "")
    step_id = body.get("step_id", 0)
    total = body.get("total", 0)
    description = body.get("description", "")
    command = body.get("command", "")
    output = body.get("output", "")
    success = body.get("success", True)
    remaining = body.get("remaining", [])

    # Build evaluation prompt
    eval_prompt = STEP_EVAL_PROMPT.format(
        goal=goal,
        step_id=step_id,
        total=total,
        description=description,
        command=command,
        output=output[:2000],  # Truncate long outputs
        success=success,
        remaining=json.dumps(remaining, ensure_ascii=False)[:500],
    )

    # Load NLP config
    saved = load_saved_config() or {}
    nlp_cfg = saved.get("nlp", {})
    provider = nlp_cfg.get("api_provider", "gemini")
    api_key = nlp_cfg.get("api_key", "")
    model = body.get("model") or nlp_cfg.get("model", "")

    if not api_key:
        return JSONResponse({"action": "continue"})  # Default: just continue

    try:
        text = ""
        if provider == "gemini":
            model = model or "gemini-2.0-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": eval_prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512},
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        elif provider in ("openai", "custom"):
            endpoint = nlp_cfg.get("endpoint", "") or "https://api.openai.com/v1/chat/completions"
            model = model or "gpt-4o"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": eval_prompt}],
                "temperature": 0.1, "max_tokens": 512,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, headers=headers) as resp:
                    data = await resp.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        elif provider == "anthropic":
            model = model or "claude-sonnet-4-20250514"
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
            payload = {"model": model, "max_tokens": 512, "messages": [{"role": "user", "content": eval_prompt}]}
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers) as resp:
                    data = await resp.json()
                    text = data.get("content", [{}])[0].get("text", "")

        elif provider == "ollama":
            ollama_url = nlp_cfg.get("ollama_url", "http://localhost:11434")
            model = nlp_cfg.get("ollama_model", model or "llama3.1:8b")
            payload = {"model": model, "messages": [{"role": "user", "content": eval_prompt}], "stream": False}
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{ollama_url}/api/chat", json=payload) as resp:
                    data = await resp.json()
                    text = data.get("message", {}).get("content", "")

        # Parse the evaluation result
        result = _parse_llm_response(text)
        # If it parsed into a chat/ssh instead of an action, default to continue
        if "action" not in result:
            return JSONResponse({"action": "continue"})
        return JSONResponse(result)

    except Exception as e:
        # On error, default to continue (don't block the plan)
        return JSONResponse({"action": "continue", "_error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("test_server:app", host="0.0.0.0", port=8090, reload=True)
