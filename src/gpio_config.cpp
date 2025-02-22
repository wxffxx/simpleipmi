#include "gpio_config.h"

// 使用任务确保 GPIO 操作的隔离性
static void gpio_task(void *arg) {
    gpio_num_t gpio_num = (gpio_num_t)(intptr_t)arg;

    gpio_set_level(gpio_num, 1);          // 设置高电平
    vTaskDelay(pdMS_TO_TICKS(1000));      // 延迟 1 秒
    gpio_set_level(gpio_num, 0);          // 拉低电平

    vTaskDelete(NULL);                    // 任务结束后删除自身
}

// ✅ GPIO 初始化
void gpio_init(void) {
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << GPIO_POWER) | (1ULL << GPIO_RESET), // 同时配置 GPIO_POWER 和 GPIO_RESET
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&io_conf);
}

// ✅ GPIO 设置高电平 1 秒然后拉低
void gpio_set_high_and_low(gpio_num_t gpio_num) {
    xTaskCreate(gpio_task, "gpio_task", 2048, (void *)gpio_num, 10, NULL);
}

// ✅ GPIO 状态读取
bool get_gpio_state(gpio_num_t gpio_num) {
    return gpio_get_level(gpio_num) == 1;
}
