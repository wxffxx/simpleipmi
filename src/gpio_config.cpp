#include "gpio_config.h"

static const char *TAG = "GPIO";  // ✅ 添加此行，定义 TAG

static QueueHandle_t gpio_evt_queue = NULL;

// ✅ GPIO 中断处理函数 (只发送事件，不打印日志)
static void IRAM_ATTR gpio_isr_handler(void *arg) {
    uint32_t gpio_num = (uint32_t)arg;
    xQueueSendFromISR(gpio_evt_queue, &gpio_num, NULL);
}

// ✅ GPIO 事件处理任务 (在这里使用 ESP_LOGI)
static void gpio_event_task(void *arg) {
    uint32_t gpio_num;
    while (1) {
        if (xQueueReceive(gpio_evt_queue, &gpio_num, portMAX_DELAY)) {
            if (gpio_num == GPIO_PWR_LED) {
                ESP_LOGI(TAG, "⚡ Power LED state changed: %s", gpio_get_level((gpio_num_t)gpio_num) ? "HIGH" : "LOW");
            } else if (gpio_num == GPIO_DISK_RESET) {
                ESP_LOGI(TAG, "💾 Disk Reset state changed: %s", gpio_get_level((gpio_num_t)gpio_num) ? "HIGH" : "LOW");
            }
        }
    }
}


// 使用任务确保 GPIO 操作的隔离性
static void gpio_task(void *arg) {
    gpio_num_t gpio_num = (gpio_num_t)(intptr_t)arg;

    gpio_set_level(gpio_num, 1);
    vTaskDelay(pdMS_TO_TICKS(1000));
    gpio_set_level(gpio_num, 0);

    vTaskDelete(NULL); 
}

// ✅ GPIO 初始化 (包括输入引脚和中断)
void gpio_init(void) {
    // 输出配置
    gpio_config_t io_conf_out = {
        .pin_bit_mask = (1ULL << GPIO_POWER) | (1ULL << GPIO_RESET),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&io_conf_out);

    // 输入配置 (启用中断)
    gpio_config_t io_conf_in = {
        .pin_bit_mask = (1ULL << GPIO_PWR_LED) | (1ULL << GPIO_DISK_RESET),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_ANYEDGE
    };
    gpio_config(&io_conf_in);

    // ✅ 创建队列
    gpio_evt_queue = xQueueCreate(10, sizeof(uint32_t));

    // ✅ 安装 ISR 服务
    gpio_install_isr_service(0);
    gpio_isr_handler_add(GPIO_PWR_LED, gpio_isr_handler, (void *)GPIO_PWR_LED);
    gpio_isr_handler_add(GPIO_DISK_RESET, gpio_isr_handler, (void *)GPIO_DISK_RESET);

    // ✅ 创建事件处理任务
    xTaskCreate(gpio_event_task, "gpio_event_task", 4096, NULL, 10, NULL);

    ESP_LOGI(TAG, "✅ GPIO initialized with interrupts");
}

// ✅ GPIO 设置高电平 1 秒然后拉低
void gpio_set_high_and_low(gpio_num_t gpio_num) {
    xTaskCreate(gpio_task, "gpio_task", 2048, (void *)gpio_num, 10, NULL);
}

// ✅ GPIO 状态读取
bool get_gpio_state(gpio_num_t gpio_num) {
    return gpio_get_level(gpio_num) == 1;
}
