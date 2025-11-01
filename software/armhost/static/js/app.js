// static/js/app.js

document.addEventListener('DOMContentLoaded', () => {
    const nodeList = document.getElementById('node-list');
    const nodeSelector = document.getElementById('node-selector');
    const addNodeForm = document.getElementById('add-node-form');
    const statusBar = document.getElementById('status-bar');
    
    let nodes = [];

    // --- API 调用函数 ---

    // 获取所有节点
    const fetchNodes = async () => {
        try {
            const response = await fetch('/api/nodes');
            nodes = await response.json();
            render();
        } catch (error) {
            updateStatusBar('无法加载节点列表', 'error');
        }
    };

    // 获取所有节点的状态
    const fetchStatuses = async () => {
        try {
            const response = await fetch('/api/status');
            const statuses = await response.json();
            updateStatusUI(statuses);
        } catch (error) {
            console.error('获取状态失败:', error);
        }
    };

    // --- UI 渲染函数 ---
    
    // 渲染整个节点列表和选择器
    const render = () => {
        // 清空现有列表
        nodeList.innerHTML = '';
        nodeSelector.innerHTML = '<option value="">-- 选择一个节点 --</option>';

        if (nodes.length === 0) {
            nodeList.innerHTML = '<li>暂无节点，请在下方添加。</li>';
        }

        nodes.forEach(node => {
            // 渲染节点列表项
            const item = document.createElement('li');
            item.className = 'node-item';
            item.dataset.address = node.address;
            item.innerHTML = `
                <div class="node-info">
                    <div class="status-indicator unknown" title="状态未知"></div>
                    <div>
                        <span class="node-name">${node.name}</span>
                        <span class="node-address">${node.address}</span>
                    </div>
                </div>
                <button class="delete-btn" data-address="${node.address}">删除</button>
            `;
            nodeList.appendChild(item);
        });
    };
    
    // 根据状态数据更新UI
    const updateStatusUI = (statuses) => {
        document.querySelectorAll('.node-item').forEach(item => {
            const address = item.dataset.address;
            const indicator = item.querySelector('.status-indicator');
            const status = statuses[address] || 'offline';
            
            indicator.className = `status-indicator ${status}`;
            indicator.title = `状态: ${status}`;
        });

        // 更新下拉选择器，只包含在线的节点
        const currentSelected = nodeSelector.value;
        nodeSelector.innerHTML = '<option value="">-- 选择一个在线节点 --</option>';
        nodes.forEach(node => {
            if (statuses[node.address] === 'online') {
                const option = document.createElement('option');
                option.value = node.address;
                option.textContent = `${node.name} (${node.address})`;
                nodeSelector.appendChild(option);
            }
        });
        nodeSelector.value = currentSelected; // 尝试恢复之前的选择
    };
    
    // 更新底部状态栏
    const updateStatusBar = (message, type = 'info', duration = 3000) => {
        statusBar.textContent = message;
        statusBar.className = `status-bar ${type}`;
        setTimeout(() => {
            statusBar.className = 'status-bar';
            statusBar.textContent = '就绪';
        }, duration);
    };

    // --- 事件监听 ---

    // 处理添加节点表单
    addNodeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const nameInput = document.getElementById('node-name');
        const addressInput = document.getElementById('node-address');
        
        const response = await fetch('/api/nodes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: nameInput.value, address: addressInput.value }),
        });
        
        const result = await response.json();
        if (response.ok) {
            updateStatusBar(result.message, 'success');
            nameInput.value = '';
            addressInput.value = '';
            fetchNodes(); // 重新加载节点列表
        } else {
            updateStatusBar(result.message, 'error');
        }
    });

    // 处理删除按钮（事件委托）
    nodeList.addEventListener('click', async (e) => {
        if (e.target.classList.contains('delete-btn')) {
            const address = e.target.dataset.address;
            if (confirm(`确定要删除节点 ${address} 吗？`)) {
                const response = await fetch(`/api/nodes/${address}`, { method: 'DELETE' });
                const result = await response.json();
                if (response.ok) {
                    updateStatusBar(result.message, 'success');
                    fetchNodes(); // 重新加载
                } else {
                    updateStatusBar(result.message, 'error');
                }
            }
        }
    });

    // --- 初始化和定时任务 ---
    fetchNodes();
    setInterval(fetchStatuses, 5000); // 每5秒刷新一次状态
    updateStatusBar('就绪');
});

// 全局发送命令函数
async function sendCommand(commandName) {
    const nodeAddress = document.getElementById('node-selector').value;
    const statusBar = document.getElementById('status-bar');

    if (!nodeAddress) {
        alert('请先选择一个在线的节点！');
        return;
    }
    
    statusBar.textContent = `正在向 ${nodeAddress} 发送命令...`;
    statusBar.className = 'status-bar';
    
    try {
        const response = await fetch('/send_command_to_node', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_address: nodeAddress, command: commandName }),
        });
        const result = await response.json();
        if (response.ok) {
            statusBar.textContent = `命令成功: ${result.message}`;
            statusBar.className = 'status-bar success';
        } else {
            statusBar.textContent = `命令失败: ${result.message}`;
            statusBar.className = 'status-bar error';
        }
    } catch (error) {
        statusBar.textContent = `网络错误: ${error}`;
        statusBar.className = 'status-bar error';
    }
    
    setTimeout(() => {
        statusBar.className = 'status-bar';
        statusBar.textContent = '就绪';
    }, 4000);
}