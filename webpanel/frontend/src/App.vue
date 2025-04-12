<template>
  <div class="layout">
    <!-- Sidebar -->
    <div class="sidebar">
      <h2 class="title">Control Panel</h2>
      <ul class="menu">
        <li :class="{ active: currentPage === 'dashboard' }" @click="currentPage = 'dashboard'">Dashboard</li>
        <li :class="{ active: currentPage === 'nodes' }" @click="currentPage = 'nodes'">Nodes</li>
        <li :class="{ active: currentPage === 'users' }" @click="currentPage = 'users'">Users</li>
        <li :class="{ active: currentPage === 'settings' }" @click="currentPage = 'settings'">Settings</li>
      </ul>
    </div>

    <!-- Main content -->
    <div class="main">
      <div class="header">Current Page: {{ pageLabel }}</div>
      <div class="content">
        <div v-if="currentPage === 'dashboard'">
          <div class="card-container">
            <div class="card">
              <h3>Node Overview</h3>
              <p>Online Nodes: {{ nodeInfo.online }} / {{ nodeInfo.total }}</p>
            </div>

            <div class="card system-info">
              <h3>System Resources</h3>
              <table class="info-table">
                <tbody>
                  <tr><td>CPU Usage:</td><td>{{ systemMeta['cpu_ usage'] }}%</td></tr>
                  <tr><td>Memory Usage:</td><td>{{ systemMeta['memory_ usage'] }}%</td></tr>
                </tbody>
              </table>
            </div>

            <div class="card system-info full-width">
              <h3>System Information</h3>
              <table class="info-table">
                <tbody>
                  <tr><td>Panel Version</td><td>{{ systemMeta.panel }}</td></tr>
                  <tr><td>Node Version</td><td>{{ systemMeta.nodeVersion }}</td></tr>
                  <tr><td>Process User</td><td>{{ systemMeta.user }}</td></tr>
                  <tr><td>Panel Time</td><td>{{ systemMeta.panelTime }}</td></tr>
                  <tr><td>Browser Time</td><td>{{ browserTime }}</td></tr>
                  <tr><td>Memory</td><td>{{ systemMeta.memory }}</td></tr>
                  <tr><td>Panel Memory Usage</td><td>{{ systemMeta.panelMemory }}</td></tr>
                  <tr><td>Hostname</td><td>{{ systemMeta.hostname }}</td></tr>
                  <tr><td>OS Version</td><td>{{ systemMeta.os }}</td></tr>
                  <tr><td>Platform</td><td>{{ systemMeta.platform }}</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div v-else-if="currentPage === 'nodes'">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <h2>Node List</h2>
            <button @click="currentPage = 'createNode'">New Node</button>
          </div>
          <div class="card-container" style="margin-top: 20px;">
            <div v-for="node in nodeInfo.list" :key="node.ip" class="card" @click="openNode(node)">
              <h3>{{ node.name }}</h3>
              <p>Type: {{ node.type }}</p>
              <p>IP: {{ node.ip }}</p>
            </div>
          </div>
        </div>

        <div v-else-if="currentPage === 'createNode'">
          <h2>Create Node</h2>
          <div class="card" style="max-width: 400px;">
            <div class="form-group">
              <label>Node Name:</label>
              <input v-model="newNodeName" type="text" placeholder="Enter Node Name" />
            </div>

            <div class="form-group">
              <label>Node Type:</label>
              <select v-model="newNodeType">
                <option value="armlinux">armlinux</option>
                <option value="esp32s2">esp32s2</option>
              </select>
            </div>

            <div class="form-group">
              <label>IP Address:</label>
              <input v-model="newNodeIP" type="text" placeholder="Enter Node IP" />
            </div>

            <div style="margin-top: 20px;">
              <button @click="createNode">Create</button>
              <button @click="currentPage = 'nodes'" style="margin-left: 10px;">Cancel</button>
            </div>
          </div>
        </div>

        <div v-else-if="currentPage === 'nodeDetail'">
          <h2>Manage Node</h2>
          <div class="card" style="max-width: 400px;">
            <p><strong>Name:</strong> {{ selectedNode.name }}</p>
            <p><strong>Type:</strong> {{ selectedNode.type }}</p>
            <p><strong>IP:</strong> {{ selectedNode.ip }}</p>

            <div v-if="selectedNode.type === 'esp32s2'" style="margin-top: 20px;">
              <h4>Send Command:</h4>
              <button v-for="cmd in commands" :key="cmd" style="margin: 4px;" @click="sendCommand(cmd)">{{ cmd }}</button>
            </div>

            <div style="margin-top: 20px;">
              <button @click="currentPage = 'nodes'">Back</button>
            </div>
          </div>
        </div>

        <div v-else-if="currentPage === 'users'">
          <h2>User Management</h2>
        </div>
        <div v-else-if="currentPage === 'settings'">
          <h2>Settings</h2>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const currentPage = ref('dashboard')
const pageLabel = computed(() => {
  switch (currentPage.value) {
    case 'dashboard': return '仪表盘'
    case 'nodes': return '节点'
    case 'createNode': return '新建节点'
    case 'nodeDetail': return '节点管理'
    case 'users': return '用户'
    case 'settings': return '设置'
    default: return ''
  }
})

const nodeInfo = ref({ total: 0, online: 0, list: [] })
const systemMeta = ref({})
const browserTime = ref("")
const newNodeName = ref("")
const newNodeType = ref("armlinux")
const newNodeIP = ref("")
const selectedNode = ref(null)
const commands = ["Start", "Stop", "Restart", "Update", "Ping"]

const fetchDashboardData = () => {
  fetch('http://localhost:8000/api/nodes')
    .then(res => res.json())
    .then(data => nodeInfo.value = data)

  fetch('http://localhost:8000/api/systeminfo')
    .then(res => res.json())
    .then(data => systemMeta.value = data)
}

const updateBrowserTime = () => {
  const now = new Date()
  const format = (n) => String(n).padStart(2, '0')
  browserTime.value = `${now.getFullYear()}/${format(now.getMonth() + 1)}/${format(now.getDate())} ` +
                      `${format(now.getHours())}:${format(now.getMinutes())}:${format(now.getSeconds())}`
}

const createNode = () => {
  if (!newNodeIP.value) {
    alert("Please enter IP address")
    return
  }

  fetch("http://localhost:8000/api/nodes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: newNodeName.value,
      type: newNodeType.value,
      ip: newNodeIP.value
    })
  }).then(() => {
    alert("Node created")
    newNodeName.value = ""
    newNodeIP.value = ""
    newNodeType.value = "armlinux"
    currentPage.value = "nodes"
    fetchDashboardData()
  })
}

const openNode = (node) => {
  selectedNode.value = node
  currentPage.value = 'nodeDetail'
}

const sendCommand = (cmd) => {
  alert(`Sent command: ${cmd} to ${selectedNode.value.ip}`)
  // 可以在这里用 fetch 向后端发送指令请求
}

onMounted(() => {
  fetchDashboardData()
  updateBrowserTime()
  setInterval(fetchDashboardData, 2000)
  setInterval(updateBrowserTime, 1000)
})
</script>

<style scoped>
body {
  margin: 0;
  font-family: "Segoe UI", sans-serif;
}

.info-table td:first-child {
  font-weight: bold;
  color: #333;
  width: 200px;
  text-align: left;
}

.layout {
  display: flex;
  height: 100vh;
}

.sidebar {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  width: 200px;
  background-color: #2d3a4b;
  color: white;
  padding: 20px 0;
  overflow-y: auto;
}

.title {
  text-align: center;
  font-size: 18px;
  margin-bottom: 20px;
}

.menu {
  list-style: none;
  padding: 0;
}

.menu li {
  padding: 12px 20px;
  cursor: pointer;
}

.menu li:hover,
.menu li.active {
  background-color: #409eff;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-left: 200px;
}

.header {
  position: fixed;
  top: 0;
  left: 200px;
  right: 0;
  height: 60px;
  background-color: #f5f7fa;
  display: flex;
  align-items: center;
  padding-left: 20px;
  font-weight: bold;
  border-bottom: 1px solid #ddd;
  box-sizing: border-box;
  z-index: 1000;
}

.content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  margin-top: 60px;
}

.card-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: flex-start;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  min-width: 250px;
  max-width: 1000px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  box-sizing: border-box;
  flex: 1 1 300px;
}

.full-width {
  flex: 1 1 100%;
  max-width: 100%;
  margin: 0 auto;
}

.system-info {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.system-info .info-table {
  width: auto;
}

.form-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 15px;
}

.card input,
.card select {
  width: 100%;
  padding: 6px 8px;
  box-sizing: border-box;
  margin-top: 5px;
}
</style>