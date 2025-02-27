#include "wifi_config.h"

static const char *TAG = "WiFi_Config";
static int retry_num = 0;

void wifi_init_sta() {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Connecting to WiFi");
    
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 10) {
        delay(1000);
        Serial.print(".");
        retries++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi Connected!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi Connection Failed!");
    }
}

void wifi_init_ap() {
    Serial.println("🔵 Configuring WiFi AP Mode...");

    // 启动 AP 模式
    bool success = WiFi.softAP(WIFI_SSID_AP, WIFI_PASS_AP);
    
    if (success) {
        Serial.println("✅ AP Mode Started!");
        Serial.print("🔗 AP SSID: ");
        Serial.println(WIFI_SSID_AP);
        Serial.print("🌍 AP IP Address: ");
        Serial.println(WiFi.softAPIP());
    } else {
        Serial.println("❌ Failed to start AP Mode!");
    }
}
