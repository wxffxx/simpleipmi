#ifndef GPIO_CONFIG_H
#define GPIO_CONFIG_H

#include "Z_define.h"

#ifdef __cplusplus
extern "C" {
#endif

void gpio_init(void);
void gpio_set_high_and_low(gpio_num_t gpio_num);
bool get_gpio_state(gpio_num_t gpio_num);

#ifdef __cplusplus
}
#endif

#endif // GPIO_CONFIG_H
