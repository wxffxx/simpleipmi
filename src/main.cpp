#include "Z_index_html.h"
#include "Z_define.h"
#include "gpio_config.h"
#include "wifi_config.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "ESP32-WEB";
static httpd_handle_t server = NULL;
static httpd_req_t *ws_client = NULL;

// ✅ WebSocket 发送 JSON 状态
void ws_send_status() {
    if (ws_client) {
        char buffer[128];
        snprintf(buffer, sizeof(buffer),
                 "{\"power\": %s, \"disk\": %s}",
                 get_gpio_state(GPIO_PWR_LED) ? "true" : "false",
                 get_gpio_state(GPIO_DISK_RESET) ? "true" : "false");

        // 按字段声明顺序进行初始化
        httpd_ws_frame_t ws_frame = {};
        ws_frame.type = HTTPD_WS_TYPE_TEXT;   // 第1个字段: type
        ws_frame.final = true;                // 第2个字段: final
        ws_frame.fragmented = false;          // 第3个字段: fragmented
        ws_frame.payload = (uint8_t *)buffer; // 第4个字段: payload
        ws_frame.len = strlen(buffer);        // 第5个字段: len

        httpd_ws_send_frame(ws_client, &ws_frame);
    }
}

// ✅ WebSocket 事件处理器
esp_err_t ws_handler(httpd_req_t *req) {
    if (req->method == HTTP_GET) {
        ws_client = req;
        ESP_LOGI(TAG, "WebSocket client connected");
    }
    return ESP_OK;
}

// ✅ HTTP 服务器处理 GET 请求
esp_err_t http_get_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, index_html, strlen(index_html));
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

    if (httpd_start(&server, &config) == ESP_OK) {
        ESP_LOGI(TAG, "🌐 HTTP Server Started");

        static httpd_uri_t uri_get = {
            .uri = "/",
            .method = HTTP_GET,
            .handler = http_get_handler,
            .user_ctx = NULL,
            .is_websocket = false,
            .handle_ws_control_frames = false,
            .supported_subprotocol = NULL
        };
        httpd_register_uri_handler(server, &uri_get);

        static httpd_uri_t uri_toggle_power = {
            .uri = "/toggle_power",
            .method = HTTP_POST,
            .handler = power_switch_handler,
            .user_ctx = NULL,
            .is_websocket = false,
            .handle_ws_control_frames = false,
            .supported_subprotocol = NULL
        };
        httpd_register_uri_handler(server, &uri_toggle_power);

        static httpd_uri_t uri_reset = {
            .uri = "/reset",
            .method = HTTP_POST,
            .handler = reset_handler,
            .user_ctx = NULL,
            .is_websocket = false,
            .handle_ws_control_frames = false,
            .supported_subprotocol = NULL
        };
        httpd_register_uri_handler(server, &uri_reset);

        static httpd_uri_t uri_ws = {
            .uri = "/ws",
            .method = HTTP_GET,
            .handler = ws_handler,
            .user_ctx = NULL,
            .is_websocket = true,
            .handle_ws_control_frames = false,
            .supported_subprotocol = NULL
        };
        httpd_register_uri_handler(server, &uri_ws);

        ESP_LOGI(TAG, "✅ All URI handlers registered");
    } else {
        ESP_LOGE(TAG, "❌ Failed to start HTTP Server");
    }
}

// ✅ WebSocket 状态轮询任务
void ws_status_task(void *arg) {
    while (1) {
        ws_send_status();
        vTaskDelay(pdMS_TO_TICKS(100)); // 每 100ms 发送一次状态
    }
}

// ✅ `app_main()` 主函数
extern "C" void app_main(void) {
    ESP_LOGI(TAG, "=== ESP32 启动 ===");

    gpio_init();
    wifi_init_sta();
    start_webserver();

    xTaskCreate(ws_status_task, "ws_status_task", 2048, NULL, 10, NULL);

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
