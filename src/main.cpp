#include <stdio.h>
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define BUTTON_PIN     GPIO_NUM_23  // 按钮连接到 GPIO23
#define OUTPUT_PIN     GPIO_NUM_22  // 输出控制引脚 GPIO22
#define INPUT_PIN      GPIO_NUM_21  // 新增输入引脚 GPIO21
#define LED_PIN        GPIO_NUM_2   // 新增LED控制引脚 GPIO2
#define DELAY_MS       200          // 检测间隔 200ms

extern "C" void app_main() {
    // 配置 GPIO23 为输入模式（启用内部下拉）
    gpio_config_t btn_config = {
        .pin_bit_mask = (1ULL << BUTTON_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&btn_config);

    // 配置 GPIO21 为输入模式（启用内部下拉）
    gpio_config_t input_config = {
        .pin_bit_mask = (1ULL << INPUT_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,  // 确保默认低电平
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&input_config);

    // 配置 GPIO22 为输出模式
    gpio_config_t out_config = {
        .pin_bit_mask = (1ULL << OUTPUT_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&out_config);

    // 配置 LED_PIN 为输出模式
    gpio_config_t led_config = {
        .pin_bit_mask = (1ULL << LED_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&led_config);

    while (1) {
        // 读取按钮状态
        int button_state = gpio_get_level(BUTTON_PIN);
        // 读取 GPIO21 输入状态
        int input_state = gpio_get_level(INPUT_PIN);

        // 控制 GPIO22 输出
        gpio_set_level(OUTPUT_PIN, button_state);

        // 控制 LED 输出（GPIO21为高时点亮LED）
        gpio_set_level(LED_PIN, input_state);

        vTaskDelay(pdMS_TO_TICKS(DELAY_MS));
    }
}