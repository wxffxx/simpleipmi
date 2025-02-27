#ifndef Z_DEFINE_H
#define Z_DEFINE_H

#include <stdio.h>
#include <string.h>
#include <cstring>
#include <SPI.h>
#include <Arduino.h>

#include "WiFi.h"
#include <EthernetENC.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "nvs_flash.h"

#include "esp_event.h"
#include "esp_log.h"
#include "esp_http_server.h"


#include "driver/spi_master.h"
#include "driver/gpio.h"

#include "gpio_config.h"
#include "wifi_config.h"
#include "eth_config.h"
#include "Z_index_html.h"

#define WIFI_SSID "IOP2.4G"
#define WIFI_PASS "18936531012"

#define WIFI_SSID_AP "ESP"
#define WIFI_PASS_AP "12345678"

#define PIN_SPI_MOSI   9
#define PIN_SPI_MISO   8
#define PIN_SPI_SCLK   7
#define PIN_SPI_CS     44
#define PIN_ETH_RST    43
#define PIN_ETH_INT    6


//output
#define GPIO_POWER static_cast<gpio_num_t>(3)
#define GPIO_RESET static_cast<gpio_num_t>(4)

//input
#define GPIO_PWR_LED static_cast<gpio_num_t>(1)
#define GPIO_DISK_RESET static_cast<gpio_num_t>(2)

#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

#endif // Z_DEFINE_H