import os
import platform
import psutil
import json
from datetime import datetime
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许跨域（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NODE_FILE = "nodes.json"

# 工具函数：读取节点列表
def read_nodes():
    if not os.path.exists(NODE_FILE):
        return []
    with open(NODE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# 工具函数：写入节点列表
def write_nodes(data):
    with open(NODE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ✅ GET: 获取节点状态
@app.get("/api/nodes")
def get_nodes_status():
    nodes = read_nodes()
    return {
        "total": len(nodes),
        "online": len(nodes),  # 此处默认所有节点在线
        "list": nodes
    }

# ✅ POST: 添加节点
@app.post("/api/nodes")
def add_node(info: dict = Body(...)):
    nodes = read_nodes()

    for node in nodes:
        if node["ip"] == info.get("ip"):
            return {"error": "IP already exists"}

    new_node = {
        "name": info.get("name", ""),  # ✅ 添加对 name 字段的处理
        "type": info.get("type", "unknown"),
        "ip": info.get("ip")
    }

    nodes.append(new_node)
    write_nodes(nodes)
    return {"message": "Node created", "data": new_node}


# ✅ 获取系统信息
@app.get("/api/systeminfo")
def get_system_info():
    mem = psutil.virtual_memory()

    return {
        "panel": "0.0.0",
        "nodeVersion": "0.1.0",
        "user": os.getlogin(),
        "panelTime": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        "tempBanned": 0,
        "blocked": 2,
        "cpu_ usage": psutil.cpu_percent(interval=0.5),
        "memory_ usage": mem.percent,
        "memory": f"{round(mem.used / 1024**3, 1)}GB / {round(mem.total / 1024**3, 1)}GB",
        "panelMemory": f"{round(psutil.Process().memory_info().rss / 1024**2, 1)}MB",
        "hostname": platform.node(),
        "os": platform.platform(),
        "platform": f"{platform.system()} {platform.architecture()[0]}"
    }
