#ifndef Z_DEFINE_H
#define Z_DEFINE_H

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_http_server.h"
#include "driver/gpio.h"
#include <cstring>
#include "esp_wifi.h"

#define WIFI_SSID "REDMI"
#define WIFI_PASS "20031103"
#define WIFI_SSID_AP "ESP"
#define WIFI_PASS_AP "12345678"

//output
#define GPIO_POWER static_cast<gpio_num_t>(7)
#define GPIO_RESET static_cast<gpio_num_t>(44)

//input
#define GPIO_PWR_LED static_cast<gpio_num_t>(9)
#define GPIO_DISK_RESET static_cast<gpio_num_t>(8)

#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

#endif // Z_DEFINE_H