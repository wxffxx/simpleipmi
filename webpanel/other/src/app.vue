<template>
    <div class="container">
      <h1>🖥️ 系统状态监控</h1>
      <div class="card">
        <p><strong>CPU 使用率：</strong> {{ cpu }}%</p>
        <p><strong>内存使用率：</strong> {{ memory }}%</p>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  
  const cpu = ref(0)
  const memory = ref(0)
  
  function fetchData() {
    fetch("http://localhost:8000/status")
      .then(res => res.json())
      .then(data => {
        cpu.value = data.cpu
        memory.value = data.memory
      })
  }
  
  // 每 1 秒更新一次
  onMounted(() => {
    fetchData()
    setInterval(fetchData, 1000)
  })
  </script>
  
  <style scoped>
  .container {
    text-align: center;
    font-family: Arial, sans-serif;
    margin-top: 50px;
  }
  .card {
    border: 1px solid #ccc;
    border-radius: 8px;
    display: inline-block;
    padding: 20px;
    margin-top: 20px;
    background-color: #f9f9f9;
  }
  </style>
  