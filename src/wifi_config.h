#ifndef WIFI_CONFIG_H
#define WIFI_CONFIG_H

#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "nvs_flash.h"

#include <cstring>


// WiFi SSID 和密码
#define WIFI_SSID "REDMI"
#define WIFI_PASS "20031103"
#define WIFI_SSID_AP "ESP"
#define WIFI_PASS_AP "12345678"

// 事件位定义
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

// 外部变量声明
extern EventGroupHandle_t wifi_event_group;

// 函数声明
void wifi_init_sta(void);
void wifi_init_ap(void);

#endif // WIFI_CONFIG_H
