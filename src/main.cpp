#include <stdio.h>
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define BUTTON_PIN     GPIO_NUM_23  // 按钮连接到 GPIO23
#define OUTPUT_PIN     GPIO_NUM_22  // 输出控制引脚 GPIO22
#define DELAY_MS       200          // 检测间隔 200ms

extern "C" void app_main() {
    // 配置 GPIO23 为输入模式（启用内部下拉，默认低电平）
    gpio_config_t btn_config = {
        .pin_bit_mask = (1ULL << BUTTON_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,  // 启用下拉，确保未按下时为低电平
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&btn_config);

    // 配置 GPIO22 为输出模式
    gpio_config_t out_config = {
        .pin_bit_mask = (1ULL << OUTPUT_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&out_config);

    while (1) {
        // 读取按钮状态
        int button_state = gpio_get_level(BUTTON_PIN);

        // 当按钮按下（高电平）时，设置 GPIO22 为高电平
        if (button_state == 1) {
            gpio_set_level(OUTPUT_PIN, 1);  // 输出高电平
            printf("Button Pressed: GPIO22 set HIGH\n");
        } else {
            gpio_set_level(OUTPUT_PIN, 0);  // 否则输出低电平
            printf("Button Released: GPIO22 set LOW\n");
        }

        // 延时 200ms（使用 FreeRTOS 标准延时宏）
        vTaskDelay(pdMS_TO_TICKS(DELAY_MS));
    }
}