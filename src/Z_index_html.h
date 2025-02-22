#ifndef Z_INDEX_HTML_H
#define Z_INDEX_HTML_H

// 将 index.html 的内容以字符串的形式嵌入到程序中
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
        }
        .led-on { background-color: green; } /* 亮起状态 */
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

        document.getElementById("power_switch").addEventListener("click", function() {
            fetch("/toggle_power", { method: "POST" })
                .then(response => response.json())
                .then(data => {
                    powerLed.className = data.power ? "led led-on" : "led";
                });
        });

        document.getElementById("reset").addEventListener("click", function() {
            fetch("/reset", { method: "POST" })
                .then(response => response.json())
                .then(data => {
                    diskLed.className = data.disk ? "led led-on" : "led";
                });
        });

        // WebSocket for real-time LED updates
        const socket = new WebSocket(`ws://${window.location.host}/ws`);

        socket.onmessage = function(event) {
            const status = JSON.parse(event.data);
            powerLed.className = status.power ? "led led-flash" : "led";
            diskLed.className = status.disk ? "led led-flash" : "led";
        };
    </script>
</body>
</html>
)rawliteral";

#endif // INDEX_HTML_H
