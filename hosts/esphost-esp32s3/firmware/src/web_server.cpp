/**
 * SI BMC — Web Server Implementation
 * AsyncWebServer + WebSocket + Simple Password Auth + SPIFFS
 */

#include "web_server.h"
#include "config.h"
#include "usb_hid.h"
#include "gpio_ctrl.h"
#include "network.h"

#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>

WebServerManager webServer;

// ─── Globals ──────────────────────────────────────────────
static AsyncWebServer server(WEB_SERVER_PORT);
static AsyncWebSocket ws("/ws/hid");

static uint32_t _startTime = 0;

// ─── Auth Helper ──────────────────────────────────────────
bool WebServerManager::_checkAuth(const String& password) {
    // If no password is set, auth is disabled
    if (strlen(AUTH_PASSWORD) == 0) return true;
    return password == AUTH_PASSWORD;
}

// Check auth from request header or query param
static bool checkRequestAuth(AsyncWebServerRequest* request) {
    if (strlen(AUTH_PASSWORD) == 0) return true;
    
    // Check Authorization header: "Bearer <password>"
    if (request->hasHeader("Authorization")) {
        String auth = request->header("Authorization");
        if (auth.startsWith("Bearer ")) {
            String token = auth.substring(7);
            if (token == AUTH_PASSWORD) return true;
        }
    }
    // Check query parameter ?auth=<password>
    if (request->hasParam("auth")) {
        if (request->getParam("auth")->value() == AUTH_PASSWORD) return true;
    }
    return false;
}

// ─── Log Buffer ───────────────────────────────────────────
void WebServerManager::addLog(const char* message, const char* level) {
    LogEntry& entry = _logs[_logHead];
    
    uint32_t sec = (millis() - _startTime) / 1000;
    uint32_t h = sec / 3600;
    uint32_t m = (sec % 3600) / 60;
    uint32_t s = sec % 60;
    snprintf(entry.time, sizeof(entry.time), "%02lu:%02lu:%02lu", h, m, s);
    
    strncpy(entry.level, level, sizeof(entry.level) - 1);
    entry.level[sizeof(entry.level) - 1] = '\0';
    strncpy(entry.message, message, sizeof(entry.message) - 1);
    entry.message[sizeof(entry.message) - 1] = '\0';
    
    _logHead = (_logHead + 1) % MAX_LOGS;
    if (_logCount < MAX_LOGS) _logCount++;
    
    // Also send to all WebSocket clients
    JsonDocument doc;
    doc["type"] = "log";
    doc["time"] = entry.time;
    doc["level"] = entry.level;
    doc["message"] = entry.message;
    
    String json;
    serializeJson(doc, json);
    ws.textAll(json);
}

String WebServerManager::getLogsJSON(int count) {
    JsonDocument doc;
    JsonArray arr = doc.to<JsonArray>();
    
    int start = (_logCount < MAX_LOGS) ? 0 : _logHead;
    int total = min(count, _logCount);
    int begin_idx = (_logCount < MAX_LOGS) ? max(0, _logCount - total)
                                           : (_logHead - total + MAX_LOGS) % MAX_LOGS;
    
    for (int i = 0; i < total; i++) {
        int idx = (begin_idx + i) % MAX_LOGS;
        JsonObject entry = arr.add<JsonObject>();
        entry["time"] = _logs[idx].time;
        entry["level"] = _logs[idx].level;
        entry["message"] = _logs[idx].message;
    }
    
    String result;
    serializeJson(doc, result);
    return result;
}

// ─── WebSocket Events ─────────────────────────────────────
static void onWsEvent(AsyncWebSocket* server, AsyncWebSocketClient* client,
                       AwsEventType type, void* arg, uint8_t* data, size_t len) {
    switch (type) {
        case WS_EVT_CONNECT:
            Serial.printf("[WS] Client #%u connected from %s\n", client->id(),
                         client->remoteIP().toString().c_str());
            webServer.addLog("HID client connected");
            break;
            
        case WS_EVT_DISCONNECT:
            Serial.printf("[WS] Client #%u disconnected\n", client->id());
            webServer.addLog("HID client disconnected");
            break;
            
        case WS_EVT_DATA: {
            AwsFrameInfo* info = (AwsFrameInfo*)arg;
            if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
                // Parse JSON message
                data[len] = 0;  // null-terminate
                
                JsonDocument doc;
                DeserializationError err = deserializeJson(doc, (char*)data);
                if (err) {
                    Serial.printf("[WS] JSON parse error: %s\n", err.c_str());
                    return;
                }
                
                JsonObject msg = doc.as<JsonObject>();
                usbHID.handleMessage(msg);
            }
            break;
        }
        
        case WS_EVT_PONG:
        case WS_EVT_ERROR:
            break;
    }
}

// ─── Route Setup ──────────────────────────────────────────
void WebServerManager::_setupRoutes() {
    // ── Serve static files from SPIFFS ──
    // Dashboard
    server.on("/", HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(SPIFFS, "/index.html", "text/html");
    });

    // HID Control page
    server.on("/hid", HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(SPIFFS, "/hid.html", "text/html");
    });

    // Static assets (CSS, JS)
    server.serveStatic("/css/", SPIFFS, "/css/").setCacheControl("max-age=3600");
    server.serveStatic("/js/", SPIFFS, "/js/").setCacheControl("max-age=3600");
    server.serveStatic("/assets/", SPIFFS, "/assets/").setCacheControl("max-age=86400");

    // ── Auth API ──
    server.on("/api/auth", HTTP_POST, [this](AsyncWebServerRequest* request) {},
        NULL,
        [this](AsyncWebServerRequest* request, uint8_t* data, size_t len, size_t index, size_t total) {
            JsonDocument doc;
            deserializeJson(doc, (char*)data);
            String password = doc["password"] | "";
            
            if (_checkAuth(password)) {
                request->send(200, "application/json", "{\"success\":true,\"token\":\"" + password + "\"}");
            } else {
                request->send(401, "application/json", "{\"success\":false,\"error\":\"密码错误\"}");
            }
        }
    );

    // ── System Status API ──
    server.on("/api/status", HTTP_GET, [this](AsyncWebServerRequest* request) {
        JsonDocument doc;
        
        doc["version"] = BMC_VERSION;
        doc["hostname"] = BMC_HOSTNAME;
        doc["uptime"] = millis() / 1000;
        doc["freeHeap"] = ESP.getFreeHeap();
        doc["chipModel"] = ESP.getChipModel();
        doc["cpuFreq"] = ESP.getCpuFreqMHz();
        
        // Temperature (ESP32-S3 internal sensor)
        #ifdef SOC_TEMP_SENSOR_SUPPORTED
        doc["temperature"] = temperatureRead();
        #else
        doc["temperature"] = 0;
        #endif
        
        // Power status
        doc["powered"] = gpioCtrl.isPowered();
        doc["gpioBusy"] = gpioCtrl.isBusy();
        
        // HID status
        doc["hidReady"] = usbHID.isReady();
        
        // Network
        JsonObject net = doc["network"].to<JsonObject>();
        net["connected"] = network.isConnected();
        net["ip"] = network.getIPAddress();
        net["mac"] = network.getMACAddress();
        net["gateway"] = network.getGateway();
        net["link"] = network.getLinkStatus();
        net["mode"] = NET_USE_DHCP ? "DHCP" : "Static";
        
        // WebSocket clients
        doc["wsClients"] = ws.count();
        
        // Auth enabled?
        doc["authEnabled"] = (strlen(AUTH_PASSWORD) > 0);
        
        String response;
        serializeJson(doc, response);
        request->send(200, "application/json", response);
    });

    // ── Power Control API ──
    server.on("/api/power/on", HTTP_POST, [this](AsyncWebServerRequest* request) {
        if (!checkRequestAuth(request)) {
            request->send(401, "application/json", "{\"error\":\"未授权\"}");
            return;
        }
        gpioCtrl.powerOn();
        addLog("电源开机指令已发送", "WARNING");
        request->send(200, "application/json",
            "{\"action\":\"power_on\",\"pulse_ms\":" + String(POWER_SHORT_PRESS_MS) + ",\"success\":true}");
    });

    server.on("/api/power/off", HTTP_POST, [this](AsyncWebServerRequest* request) {
        if (!checkRequestAuth(request)) {
            request->send(401, "application/json", "{\"error\":\"未授权\"}");
            return;
        }
        gpioCtrl.powerOff();
        addLog("强制关机指令已发送", "WARNING");
        request->send(200, "application/json",
            "{\"action\":\"power_off\",\"pulse_ms\":" + String(POWER_LONG_PRESS_MS) + ",\"success\":true}");
    });

    server.on("/api/power/reset", HTTP_POST, [this](AsyncWebServerRequest* request) {
        if (!checkRequestAuth(request)) {
            request->send(401, "application/json", "{\"error\":\"未授权\"}");
            return;
        }
        gpioCtrl.reset();
        addLog("重启指令已发送", "WARNING");
        request->send(200, "application/json",
            "{\"action\":\"reset\",\"pulse_ms\":" + String(RESET_PULSE_MS) + ",\"success\":true}");
    });

    server.on("/api/power/status", HTTP_GET, [](AsyncWebServerRequest* request) {
        JsonDocument doc;
        doc["powered"] = gpioCtrl.isPowered();
        doc["busy"] = gpioCtrl.isBusy();
        
        String response;
        serializeJson(doc, response);
        request->send(200, "application/json", response);
    });

    // ── Logs API ──
    server.on("/api/logs", HTTP_GET, [this](AsyncWebServerRequest* request) {
        int count = 50;
        if (request->hasParam("n")) {
            count = request->getParam("n")->value().toInt();
            count = constrain(count, 1, 200);
        }
        String logs = getLogsJSON(count);
        request->send(200, "application/json", "{\"logs\":" + logs + "}");
    });

    // ── GPIO Status API ──
    server.on("/api/gpio/status", HTTP_GET, [](AsyncWebServerRequest* request) {
        JsonDocument doc;
        
        JsonObject pwr = doc["power"].to<JsonObject>();
        pwr["pin"] = PIN_PWR_BTN;
        pwr["active_low"] = PWR_ACTIVE_LOW;
        pwr["short_press_ms"] = POWER_SHORT_PRESS_MS;
        pwr["long_press_ms"] = POWER_LONG_PRESS_MS;
        
        JsonObject rst = doc["reset"].to<JsonObject>();
        rst["pin"] = PIN_RST_BTN;
        rst["active_low"] = RST_ACTIVE_LOW;
        rst["pulse_ms"] = RESET_PULSE_MS;
        
        JsonObject status = doc["power_detect"].to<JsonObject>();
        status["pin"] = PIN_PWR_LED;
        status["active_low"] = PWR_LED_ACTIVE_LOW;
        status["powered"] = gpioCtrl.isPowered();
        
        String response;
        serializeJson(doc, response);
        request->send(200, "application/json", response);
    });

    // ── 404 ──
    server.onNotFound([](AsyncWebServerRequest* request) {
        request->send(404, "application/json", "{\"error\":\"Not found\"}");
    });
}

// ─── WebSocket Setup ──────────────────────────────────────
void WebServerManager::_setupWebSocket() {
    ws.onEvent(onWsEvent);
    server.addHandler(&ws);
}

// ─── Begin ────────────────────────────────────────────────
void WebServerManager::begin() {
    _startTime = millis();
    
    // Initialize SPIFFS
    if (!SPIFFS.begin(true)) {
        Serial.println("[WEB] SPIFFS mount failed!");
        return;
    }
    Serial.println("[WEB] SPIFFS mounted");

    _setupWebSocket();
    _setupRoutes();
    
    server.begin();
    Serial.printf("[WEB] Server started on port %d\n", WEB_SERVER_PORT);
    
    addLog("BMC 服务器已启动");
}
