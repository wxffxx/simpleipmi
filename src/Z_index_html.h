#ifndef Z_INDEX_HTML_H
#define Z_INDEX_HTML_H

const char index_html[] = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>Remote Control Panel</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin: 50px; }
        h1 { color: #3498db; }
        .button {
            display: inline-block;
            margin: 10px;
            padding: 15px 30px;
            font-size: 16px;
            cursor: pointer;
            border: none;
            color: white;
            background-color: #3498db;
            border-radius: 5px;
        }
        .button:hover { background-color: #2980b9; }
        .led {
            display: inline-block;
            width: 20px;
            height: 20px;
            margin: 10px;
            border-radius: 50%;
            background-color: gray; /* 默认关闭状态 */
            transition: background-color 0.3s;
        }
        .led-on { background-color: green; } /* 持续亮起状态 */
        .led-flash {
            animation: flash 0.2s infinite alternate;
        }
        @keyframes flash {
            from { background-color: green; }
            to { background-color: gray; }
        }
    </style>
</head>
<body>
    <h1>Remote Control Panel</h1>
    
    <button class="button" id="power_switch">Power Switch</button>
    <button class="button" id="reset">Reset</button>

    <h2>Status Indicators</h2>
    <p>Power LED: <span class="led" id="power_led"></span></p>
    <p>Disk LED: <span class="led" id="disk_led"></span></p>

    <script>
        const powerLed = document.getElementById("power_led");
        const diskLed = document.getElementById("disk_led");

        // ✅ 电源开关按钮
        document.getElementById("power_switch").addEventListener("click", function() {
            fetch("/toggle_power", { method: "POST" })
                .then(response => response.json())
                .then(data => {
                    powerLed.className = data.power ? "led led-on" : "led";
                });
        });

        // ✅ 重置按钮
        document.getElementById("reset").addEventListener("click", function() {
            fetch("/reset", { method: "POST" })
                .then(response => response.json())
                .then(data => {
                    diskLed.className = data.disk ? "led led-on" : "led";
                });
        });

        // ✅ 状态记录
        let powerLedState = false;
        let diskLedState = false;

        // ✅ 定时轮询 LED 状态
        function fetchStatus() {
            fetch("/status")
                .then(response => response.json())
                .then(data => {
                    // 如果检测到高电平则亮起，否则保持上一次状态
                    powerLedState = data.power || powerLedState;
                    diskLedState = data.disk || diskLedState;

                    powerLed.className = powerLedState ? "led led-on" : "led";
                    diskLed.className = diskLedState ? "led led-on" : "led";

                    // 如果 500ms 内未检测到高电平则熄灭
                    if (!data.power) powerLedState = false;
                    if (!data.disk) diskLedState = false;
                })
                .catch(error => console.warn("Status fetch error:", error));
        }

        // ✅ 每500ms轮询一次状态
        setInterval(fetchStatus, 500);
    </script>
</body>
</html>
)rawliteral";

#endif // INDEX_HTML_H
