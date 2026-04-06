/**
 * SI BMC — Web Server Module Header
 * AsyncWebServer + WebSocket for HID events + simple password auth
 */
#pragma once

#include <Arduino.h>

// Log buffer for dashboard display
struct LogEntry {
    char time[12];
    char level[8];
    char message[128];
};

class WebServerManager {
public:
    void begin();
    void addLog(const char* message, const char* level = "INFO");
    String getLogsJSON(int count = 50);

private:
    static const int MAX_LOGS = 200;
    LogEntry _logs[200];
    int _logHead = 0;
    int _logCount = 0;

    void _setupRoutes();
    void _setupWebSocket();
    bool _checkAuth(const String& password);
};

extern WebServerManager webServer;
