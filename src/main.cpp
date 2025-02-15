#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_http_server.h"
#include "esp_mac.h"
#include "esp_wifi_types.h"
#include "lwip/ip_addr.h"
#include "esp_spiffs.h"  // 添加 SPIFFS 头文件

#define WIFI_SSID "IOP"
#define WIFI_PASS "18936531012"

static const char *TAG = "ESP32-SPIFFS";

// 初始化 SPIFFS
void init_spiffs() {
    ESP_LOGI(TAG, "Initializing SPIFFS");

    esp_vfs_spiffs_conf_t conf = {
        .base_path = "/spiffs",
        .partition_label = NULL,
        .max_files = 5,
        .format_if_mount_failed = true
    };

    ESP_ERROR_CHECK(esp_vfs_spiffs_register(&conf));
    ESP_LOGI(TAG, "SPIFFS mounted successfully");
}

// 读取 SPIFFS 中的 index.html 文件
esp_err_t http_get_handler(httpd_req_t *req) {
    char path[64] = "/spiffs/index.html";  // SPIFFS 目录
    FILE *file = fopen(path, "r");
    if (!file) {
        ESP_LOGE(TAG, "Failed to open file: %s", path);
        httpd_resp_send_404(req);
        return ESP_FAIL;
    }

    char buffer[1024];
    size_t read_bytes = fread(buffer, 1, sizeof(buffer), file);
    fclose(file);

    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, buffer, read_bytes);
    return ESP_OK;
}

// 配置 HTTP 服务器
httpd_uri_t uri_get = {
    .uri = "/",
    .method = HTTP_GET,
    .handler = http_get_handler,
    .user_ctx = NULL
};

// 启动 HTTP 服务器
void start_webserver(void) {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    httpd_handle_t server = NULL;
    if (httpd_start(&server, &config) == ESP_OK) {
        httpd_register_uri_handler(server, &uri_get);
        ESP_LOGI(TAG, "HTTP Server Started");
    }
}

// 连接 WiFi (STA 模式)
void wifi_init_sta(void) {
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    wifi_config_t wifi_config;
    memset(&wifi_config, 0, sizeof(wifi_config));
    strcpy((char *)wifi_config.sta.ssid, WIFI_SSID);
    strcpy((char *)wifi_config.sta.password, WIFI_PASS);

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));  // 设为 STA 模式
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));  // 配置 WiFi
    ESP_ERROR_CHECK(esp_wifi_start());  // 启动 WiFi

    ESP_LOGI(TAG, "WiFi Connected to SSID: %s", WIFI_SSID);
}

// `app_main()` 入口
extern "C" void app_main(void) {
    ESP_LOGI(TAG, "=== ESP32 启动 ===");
    wifi_init_sta();
    init_spiffs();  // 初始化 SPIFFS
    start_webserver();

    while (1) {
        vTaskDelay(10000 / portTICK_PERIOD_MS);
    }
}
