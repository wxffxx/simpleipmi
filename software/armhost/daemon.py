from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/execute', methods=['POST'])
def execute_command():
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({"status": "error", "message": "无效的请求,缺少'command'参数"}), 400

    command = data['command']
    print(f"======== 命令接收成功 ========")
    print(f"  接收到的命令: {command}")
    print(f"==============================")
    
    return jsonify({"status": "success", "message": f"命令 '{command}' 已在守护进程端打印"})

# [新增] 用于响应健康检测的接口
@app.route('/health', methods=['GET'])
def health_check():
    """
    一个简单的健康检查端点，如果服务正在运行，就返回成功。
    """
    # 为了保持终端干净，心跳检查可以不打印信息，除非你需要调试
    # print("收到一次健康检查请求...")
    return jsonify({"status": "alive"}), 200

if __name__ == '__main__':
    print("守护进程正在启动，监听地址 http://0.0.0.0:5001")
    app.run(host='0.0.0.0', port=5001)