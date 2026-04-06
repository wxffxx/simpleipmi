/**
 * SI BMC — Network Module Implementation
 * WiFi AP mode for direct connection
 */

#include "network.h"
#include "config.h"
#include <WiFi.h>

NetworkManager network;

void NetworkManager::_generateMAC() {
    uint64_t chipid = ESP.getEfuseMac();
    _mac[0] = 0xDE;
    _mac[1] = 0xAD;
    _mac[2] = (chipid >> 0) & 0xFF;
    _mac[3] = (chipid >> 8) & 0xFF;
    _mac[4] = (chipid >> 16) & 0xFF;
    _mac[5] = (chipid >> 24) & 0xFF;
}

bool NetworkManager::begin() {
    _generateMAC();

    // ── WiFi AP Mode ──
    Serial.println("[NET] Starting WiFi AP mode");
    
    WiFi.mode(WIFI_AP);
    WiFi.softAPConfig(
        IPAddress(192, 168, 4, 1),
        IPAddress(192, 168, 4, 1),
        IPAddress(255, 255, 255, 0)
    );
    
    bool ok = WiFi.softAP(AP_SSID, AP_PASSWORD);
    
    if (ok) {
        _connected = true;
        Serial.printf("[NET] AP started: SSID='%s' Password='%s'\n", AP_SSID, AP_PASSWORD);
        Serial.printf("[NET] IP: %s\n", WiFi.softAPIP().toString().c_str());
        return true;
    } else {
        _connected = false;
        Serial.println("[NET] AP start FAILED!");
        return false;
    }
}

void NetworkManager::update() {
    // AP mode doesn't need reconnection logic
    _connected = true;
}

bool NetworkManager::isConnected() {
    return _connected;
}

String NetworkManager::getIPAddress() {
    return WiFi.softAPIP().toString();
}

String NetworkManager::getMACAddress() {
    return WiFi.softAPmacAddress();
}

String NetworkManager::getGateway() {
    return "192.168.4.1";
}

String NetworkManager::getSubnet() {
    return "255.255.255.0";
}

bool NetworkManager::getLinkStatus() {
    return true;
}

String NetworkManager::getStatusJSON() {
    char buf[300];
    snprintf(buf, sizeof(buf),
        "{\"connected\":true,\"ip\":\"%s\",\"mac\":\"%s\",\"gateway\":\"192.168.4.1\","
        "\"subnet\":\"255.255.255.0\",\"link\":true,\"mode\":\"AP (%d clients)\"}",
        getIPAddress().c_str(),
        getMACAddress().c_str(),
        WiFi.softAPgetStationNum()
    );
    return String(buf);
}
