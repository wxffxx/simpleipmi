#ifndef WIFI_CONFIG_H
#define WIFI_CONFIG_H

#include "Z_define.h"

// 外部变量声明
extern EventGroupHandle_t wifi_event_group;

// 函数声明
void wifi_init_sta(void);
void wifi_init_ap(void);

#endif // WIFI_CONFIG_H
