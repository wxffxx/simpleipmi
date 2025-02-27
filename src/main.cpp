#include "Z_define.h"

static const char *TAG = "ESP32-WEB";
static httpd_handle_t server = NULL;

// ✅ HTTP 服务器处理 GET 请求 (HTML 页面)
esp_err_t http_get_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, index_html, strlen(index_html));
    return ESP_OK;
}

// ✅ HTTP 服务器处理 GPIO 状态请求 (JSON)
esp_err_t status_handler(httpd_req_t *req) {
    char buffer[128];
    snprintf(buffer, sizeof(buffer),
             "{\"power\": %s, \"disk\": %s}",
             get_gpio_state(GPIO_PWR_LED) ? "true" : "false",
             get_gpio_state(GPIO_DISK_RESET) ? "true" : "false");

    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, buffer, strlen(buffer));
    return ESP_OK;
}

// ✅ HTTP 服务器处理 Power Switch
esp_err_t power_switch_handler(httpd_req_t *req) {
    ESP_LOGI(TAG, "Power Switch Triggered");
    gpio_set_high_and_low(GPIO_POWER);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, "{\"power\": true}", strlen("{\"power\": true}"));
    return ESP_OK;
}

// ✅ HTTP 服务器处理 Reset
esp_err_t reset_handler(httpd_req_t *req) {
    ESP_LOGI(TAG, "Reset Triggered");
    gpio_set_high_and_low(GPIO_RESET);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, "{\"reset\": true}", strlen("{\"reset\": true}"));
    return ESP_OK;
}

// ✅ 启动 HTTP 服务器
void start_webserver(void) {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.lru_purge_enable = true;  // 启用资源自动释放

    if (httpd_start(&server, &config) == ESP_OK) {
        ESP_LOGI(TAG, "✅ HTTP Server started");

        static httpd_uri_t uri_get = {
            .uri = "/",
            .method = HTTP_GET,
            .handler = http_get_handler,
            .user_ctx = NULL
        };
        httpd_register_uri_handler(server, &uri_get);
        
        static httpd_uri_t uri_status = {
            .uri = "/status",
            .method = HTTP_GET,
            .handler = status_handler,
            .user_ctx = NULL
        };
        httpd_register_uri_handler(server, &uri_status);
        
        static httpd_uri_t uri_toggle_power = {
            .uri = "/toggle_power",
            .method = HTTP_POST,
            .handler = power_switch_handler,
            .user_ctx = NULL
        };
        httpd_register_uri_handler(server, &uri_toggle_power);
        
        static httpd_uri_t uri_reset = {
            .uri = "/reset",
            .method = HTTP_POST,
            .handler = reset_handler,
            .user_ctx = NULL
        };
        httpd_register_uri_handler(server, &uri_reset);

        ESP_LOGI(TAG, "✅ All URI handlers registered");
    } else {
        ESP_LOGE(TAG, "❌ Failed to start HTTP Server");
    }
}

void setup() {
    Serial.begin(115200);

    delay(5000);
    gpio_init();
    
    wifi_init_sta();
    //wifi_init_ap();
    init_ethernet();
    
    delay(2000);
    start_webserver();
}

void loop() {
    delay(10000);
}

