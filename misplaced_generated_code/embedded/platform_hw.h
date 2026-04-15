#ifndef PLATFORM_HW_H
#define PLATFORM_HW_H

#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint32_t device_id;
    uint32_t sample_period_ms;
    uint32_t flags;
} sensor_config_t;

void platform_uart_init(uint32_t baud);
void platform_uart_tx_byte(uint8_t b);
int platform_uart_rx_try(void);

int platform_flash_read(uint32_t addr, uint8_t *buf, uint32_t len);
int platform_get_config(sensor_config_t *out);

void platform_jtag_debug_pins_init(void);

#endif
