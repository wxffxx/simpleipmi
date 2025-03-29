#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <USBHIDKeyboard.h>
#include "USB.h"

#define WIFI_SSID "IOP2.4G"
#define WIFI_PASS "18936531012"
 
USBHIDKeyboard Keyboard;
WiFiServer tcpServer(8888);
WiFiClient tcpClient;

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

void wifi_init_sta() {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("正在连接WiFi");

    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 15) {
        delay(1000);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi连接成功!");
        Serial.print("IP地址: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi连接失败!");
        ESP.restart();
    }
}

void setup() {
    USB.begin();
    Keyboard.begin();
    wifi_init_sta();
    tcpServer.begin();  // 启动 TCP 服务器
}

//command: echo [key] | nc [ip] [port]
void loop() {
    if (!tcpClient || !tcpClient.connected()) {
        tcpClient = tcpServer.available();
    }

    if (tcpClient && tcpClient.available()) {
        String input = tcpClient.readStringUntil('\n');
        input.trim();
        printf("%s\n", input.c_str());
        if (input.length() > 0) {
            if (KeyPress(input.c_str()) == 0) {
                tcpClient.println("cg: " + input);
            } else {
                tcpClient.println("sb: " + input);
            }
        }
    }
}
