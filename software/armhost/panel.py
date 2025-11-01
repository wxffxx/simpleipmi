from flask import Flask, render_template, request, jsonify
import requests
import json
import time
import threading
import logging
import os

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 全局变量和锁 ---
NODES_FILE = 'nodes.json'
SETTINGS_FILE = 'setting.json'
node_statuses = {}  # 用于实时存储节点状态 e.g., {'127.0.0.1:5001': 'online'}
file_lock = threading.Lock() # 用于文件读写的线程锁

# --- 配置文件读写 ---
def load_json_file(filename, default_data):
    with file_lock:
        if not os.path.exists(filename):
            logging.warning(f"文件 {filename} 未找到，将创建默认文件。")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2)
            return default_data
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"文件 {filename} 格式错误，请检查JSON语法。")
            return default_data

def save_nodes_to_file(nodes_data):
    with file_lock:
        with open(NODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(nodes_data, f, indent=2)

# --- 加载配置 ---
settings = load_json_file(SETTINGS_FILE, {'health_check_interval_seconds': 15})
CHECK_INTERVAL = settings.get('health_check_interval_seconds')

# --- 后台健康检测任务 ---
def health_check_task():
    logging.info("后台监控线程已启动。")
    while True:
        nodes = load_json_file(NODES_FILE, []) # 每次循环重新加载节点列表
        if not nodes:
            time.sleep(CHECK_INTERVAL)
            continue

        for node in nodes:
            address = node.get("address")
            health_url = f"http://{address}/health"
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200 and response.json().get('status') == 'alive':
                    node_statuses[address] = 'online'
                else:
                    node_statuses[address] = 'offline'
            except requests.exceptions.RequestException:
                node_statuses[address] = 'offline'
        time.sleep(CHECK_INTERVAL)

# --- Flask 应用 ---
app = Flask(__name__)

# --- API Endpoints ---
@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    nodes = load_json_file(NODES_FILE, [])
    return jsonify(nodes)

@app.route('/api/nodes', methods=['POST'])
def add_node():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('address'):
        return jsonify({'message': '名称和地址不能为空'}), 400
    
    nodes = load_json_file(NODES_FILE, [])
    if any(n['address'] == data['address'] for n in nodes):
        return jsonify({'message': f"地址 {data['address']} 已存在"}), 409 # 409 Conflict

    nodes.append({'name': data['name'], 'address': data['address']})
    save_nodes_to_file(nodes)
    return jsonify({'message': '节点添加成功'}), 201

@app.route('/api/nodes/<path:address>', methods=['DELETE'])
def delete_node(address):
    nodes = load_json_file(NODES_FILE, [])
    original_length = len(nodes)
    nodes = [node for node in nodes if node.get('address') != address]
    
    if len(nodes) < original_length:
        save_nodes_to_file(nodes)
        node_statuses.pop(address, None) # 从状态字典中移除
        return jsonify({'message': '节点删除成功'}), 200
    else:
        return jsonify({'message': '未找到要删除的节点'}), 404

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(node_statuses)

# --- 页面路由 ---
@app.route('/')
def index():
    """渲染主页面框架"""
    return render_template('index.html')

# [旧功能] 命令发送接口，保持不变
@app.route('/send_command_to_node', methods=['POST'])
def send_command_to_node():
    data = request.get_json()
    node_address = data.get('node_address')
    command = data.get('command')
    daemon_url = f"http://{node_address}/execute"
    try:
        response = requests.post(daemon_url, json={"command": command}, timeout=5)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    monitor_thread = threading.Thread(target=health_check_task, daemon=True)
    monitor_thread.start()
    logging.info(f"管理面板正在启动，请访问 http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000)