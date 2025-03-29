#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <USBHIDKeyboard.h>
#include "USB.h"

#define WIFI_SSID "IOP2.4G"
#define WIFI_PASS "18936531012"

WebServer server(80);
USBHIDKeyboard Keyboard;

const char* htmlPage = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>web keyboard control</title>
    <style>
        .keyboard {
            display: flex;
            justify-content: center;
            gap: 5px;
            margin: 5px 0;
        }
        button {
            width: 50px;
            height: 50px;
            font-size: 16px;
            background-color: #f0f0f0;
            border: 2px solid #4CAF50;
            border-radius: 5px;
            cursor: pointer;
        }
        button.hold {
            background-color: #4CAF50;
            color: white;
        }
        button.active {
            background-color: #FFD700; /* Caps Lock */
        }

        #info {
            text-align: center;
            margin-top: 20px;
        }
        .wide {
            width: 80px;
        }
        .extra-wide {
            width: 100px;
        }
        .ultra-wide {
            width: 125px;
        }
        .spacebar {
            width: 350px;
        }
    </style>
</head>
<body>

<div class="keyboard">
    <button onclick="sendKey('Esc')">Esc</button>
    <button onclick="sendKey('1')">1</button>
    <button onclick="sendKey('2')">2</button>
    <button onclick="sendKey('3')">3</button>
    <button onclick="sendKey('4')">4</button>
    <button onclick="sendKey('5')">5</button>
    <button onclick="sendKey('6')">6</button>
    <button onclick="sendKey('7')">7</button>
    <button onclick="sendKey('8')">8</button>
    <button onclick="sendKey('9')">9</button>
    <button onclick="sendKey('0')">0</button>
    <button onclick="sendKey('-')">-</button>
    <button onclick="sendKey('=')">=</button>
    <button class="wide" onclick="sendKey('back')">Back</button>
</div>

<div class="keyboard">
    <button class="wide" onclick="sendKey('Tab')">Tab</button>
    <button onclick="sendKey('Q')">Q</button>
    <button onclick="sendKey('W')">W</button>
    <button onclick="sendKey('E')">E</button>
    <button onclick="sendKey('R')">R</button>
    <button onclick="sendKey('T')">T</button>
    <button onclick="sendKey('Y')">Y</button>
    <button onclick="sendKey('U')">U</button>
    <button onclick="sendKey('I')">I</button>
    <button onclick="sendKey('O')">O</button>
    <button onclick="sendKey('P')">P</button>
    <button onclick="sendKey('[')">[</button>
    <button onclick="sendKey(']')">]</button>
    <button onclick="sendKey('\\')">\</button>
</div>

<div class="keyboard">
    <button class="extra-wide" id="capsLock" onclick="toggleCapsLock()">Caps</button>
    <button onclick="sendKey('A')">A</button>
    <button onclick="sendKey('S')">S</button>
    <button onclick="sendKey('D')">D</button>
    <button onclick="sendKey('F')">F</button>
    <button onclick="sendKey('G')">G</button>
    <button onclick="sendKey('H')">H</button>
    <button onclick="sendKey('J')">J</button>
    <button onclick="sendKey('K')">K</button>
    <button onclick="sendKey('L')">L</button>
    <button onclick="sendKey(';')">;</button>
    <button onclick="sendKey('\'')">'</button>
    <button class="wide" onclick="sendKey('Enter')">Enter</button>
</div>

<div class="keyboard">
    <button class="extra-wide" id="leftShift" onclick="toggleLeftShift()">Shift</button>
    <button onclick="sendKey('Z')">Z</button>
    <button onclick="sendKey('X')">X</button>
    <button onclick="sendKey('C')">C</button>
    <button onclick="sendKey('V')">V</button>
    <button onclick="sendKey('B')">B</button>
    <button onclick="sendKey('N')">N</button>
    <button onclick="sendKey('M')">M</button>
    <button onclick="sendKey(',')">,</button>
    <button onclick="sendKey('.')">.</button>
    <button onclick="sendKey('/')">/</button>
    <button class="extra-wide" onclick="sendKey('rightshift')">Shift</button>
</div>

<div class="keyboard">
    <button id="leftCtrl" onclick="toggleLeftCtrl()">Ctrl</button>
    <button onclick="sendKey('win')">Win</button>
    <button id="leftAlt" onclick="toggleLeftAlt()">Alt</button>
    <button class="spacebar" onclick="sendKey('space')">Space</button>
    <button onclick="sendKey('rightalt')">Alt</button>
    <button onclick="sendKey('rightwin')">Win</button>
    <button onclick="sendKey('rightctrl')">Ctrl</button>
</div>

<div class="keyboard">
    <button class="ultra-wide" onclick="sendKey('ctrl+alt+del')">Ctrl+Alt+Del</button>
    <button onclick="sendKey('del')">Del</button>
    <button onclick="sendKey('f11')">F11</button>
    <button onclick="sendKey('f2')">F2</button>
</div>

<div id="info">IP地址：%IP%</div>

<script>
let leftShiftHeld = false;
let capsLockActive = false;
let leftCtrlHeld = false;
let leftAltHeld = false;

async function toggleLeftShift() {
    leftShiftHeld = !leftShiftHeld;

    const button = document.getElementById("leftShift");
    if (leftShiftHeld) {
        button.classList.add("hold");
        await fetch('/key?button=leftshift_press', {method: 'POST'});
    } else {
        button.classList.remove("hold");
        await fetch('/key?button=leftshift_release', {method: 'POST'});
    }
}

async function toggleCapsLock() {
    capsLockActive = !capsLockActive;

    const button = document.getElementById("capsLock");
    if (capsLockActive) {
        button.classList.add("active");
    } else {
        button.classList.remove("active");
    }

    await fetch('/key?button=capslock', {method: 'POST'});
}

// 左Ctrl
async function toggleLeftCtrl() {
    leftCtrlHeld = !leftCtrlHeld;
    const button = document.getElementById("leftCtrl");

    if (leftCtrlHeld) {
        button.classList.add("hold");
        await fetch('/key?button=leftctrl_press', {method: 'POST'});
    } else {
        button.classList.remove("hold");
        await fetch('/key?button=leftctrl_release', {method: 'POST'});
    }
}

// 左Alt
async function toggleLeftAlt() {
    leftAltHeld = !leftAltHeld;
    const button = document.getElementById("leftAlt");

    if (leftAltHeld) {
        button.classList.add("hold");
        await fetch('/key?button=leftalt_press', {method: 'POST'});
    } else {
        button.classList.remove("hold");
        await fetch('/key?button=leftalt_release', {method: 'POST'});
    }
}

async function sendKey(key) {
    await fetch('/key?button=' + encodeURIComponent(key), {method: 'POST'});
}
</script>

</body>
</html>
)rawliteral";

void handleRoot() {
    String page = htmlPage;
    page.replace("%IP%", WiFi.localIP().toString());
    server.send(200, "text/html", page);
}

int KeyPress(String key) {
    key.toLowerCase();

    if (key.length() == 1 && ((key[0] >= 'a' && key[0] <= 'z') || (key[0] >= '0' && key[0] <= '9'))) {
        Keyboard.print(key);
    }
    else if(key == "-" || key == "=" || key == "[" || key == "]" || key == "\\" || key == ";" || key == "'" || key == "," || key == "." || key == "/") {
        Keyboard.print(key);
    }
    
    else if (key == "back") {
        Keyboard.press(KEY_BACKSPACE);
        delay(100);
        Keyboard.release(KEY_BACKSPACE);
    }
    else if (key == "del") {
        Keyboard.press(KEY_DELETE);
        delay(100);
        Keyboard.release(KEY_DELETE);
    }
    else if (key == "f2") {
        Keyboard.press(KEY_F2);
        delay(100);
        Keyboard.release(KEY_F2);
    }
    else if (key == "f11") {
        Keyboard.press(KEY_F11);
        delay(100);
        Keyboard.release(KEY_F11);
    }
    else if (key == "ctrl+alt+del") {
        Keyboard.press(KEY_LEFT_CTRL);
        Keyboard.press(KEY_LEFT_ALT);
        Keyboard.press(KEY_DELETE);
        delay(100);
        Keyboard.releaseAll();
    }
    else if (key == "tab") {
        Keyboard.press(KEY_TAB);
        delay(100);
        Keyboard.release(KEY_TAB);
    }
    else if (key == "enter") {
        Keyboard.press(KEY_RETURN);
        delay(100);
        Keyboard.release(KEY_RETURN);
    }
    else if (key == "esc") {
        Keyboard.press(KEY_ESC);
        delay(100);
        Keyboard.release(KEY_ESC);
    }
    else if (key == "space") {
        Keyboard.press(' ');
        delay(100);
        Keyboard.release(' ');
    }

    else if (key == "capslock") {
      Keyboard.press(KEY_CAPS_LOCK);
      delay(100);
      Keyboard.release(KEY_CAPS_LOCK);
    }
    else if (key == "leftctrl_press") {
      Keyboard.press(KEY_LEFT_CTRL);
    }
    else if (key == "leftctrl_release") {
        Keyboard.release(KEY_LEFT_CTRL);
    }
    else if (key == "leftalt_press") {
        Keyboard.press(KEY_LEFT_ALT);
    }
    else if (key == "leftalt_release") {
        Keyboard.release(KEY_LEFT_ALT);
    }
    else if (key == "leftshift_press") {
      Keyboard.press(KEY_LEFT_SHIFT);
    } 
    else if (key == "leftshift_release") {
        Keyboard.release(KEY_LEFT_SHIFT);
    }

    else if (key == "rightwin") {
      Keyboard.press(KEY_LEFT_GUI);
      delay(100);
      Keyboard.release(KEY_LEFT_GUI);
    }
    else if (key == "rightalt") {
        Keyboard.press(KEY_LEFT_ALT);
        delay(100);
        Keyboard.release(KEY_LEFT_ALT);
    }
    else if (key == "rightshift") {
        Keyboard.press(KEY_RIGHT_SHIFT);
        delay(100);
        Keyboard.release(KEY_RIGHT_SHIFT);
    }
    else if (key == "rightctrl") {
        Keyboard.press(KEY_RIGHT_CTRL);
        delay(100);
        Keyboard.release(KEY_RIGHT_CTRL);
    }
    else {
        printf("invaild: ");
        Serial.println("❌" + key);
        return 1;
    }

    return 0;
}

void handleKeyPress() {
    if (!server.hasArg("button")) {
        server.send(400, "text/plain", "error: missing parameter");
        return;
    }

    String key = server.arg("button");

    
    if(KeyPress(key) == 1) {
        server.send(400, "text/plain", "invaild: " + key);
        return;
    }
    
    server.send(200, "text/plain", key + " pressed");
    Serial.println("send key: " + key);
}

void wifi_init_sta() {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Connecting WiFi");

    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 15) {
        delay(1000);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi");
        ESP.restart();
    }
}

void setup() {
    USB.begin();
    Keyboard.begin();
    wifi_init_sta();

    server.on("/", handleRoot);
    server.on("/key", HTTP_POST, handleKeyPress);
    server.begin();
}

void loop() {
    server.handleClient();
}

