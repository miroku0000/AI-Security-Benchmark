#ifndef DIAGNOSTIC_CONSOLE_H
#define DIAGNOSTIC_CONSOLE_H

#include <stdint.h>
#include <stddef.h>

void diagnostic_console_init(void);
void diagnostic_console_poll(void);

#endif

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

#include "diagnostic_console.h"
#include "platform_hw.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define SHELL_LINE_MAX        128U
#define DUMP_LINE_BYTES       16U
#define FLASH_READ_CHUNK      256U

static char line_buf[SHELL_LINE_MAX];
static size_t line_len;

static void uart_puts(const char *s)
{
    while (*s) {
        platform_uart_tx_byte((uint8_t)*s++);
    }
}

static void uart_put_hex_nibble(uint8_t n)
{
    static const char hex[] = "0123456789ABCDEF";
    platform_uart_tx_byte((uint8_t)hex[n & 0x0FU]);
}

static void uart_put_hex_u32(uint32_t v)
{
    for (int i = 7; i >= 0; --i) {
        uart_put_hex_nibble((uint8_t)((v >> (i * 4)) & 0x0FU));
    }
}

static void uart_put_hex_u8(uint8_t v)
{
    uart_put_hex_nibble((uint8_t)(v >> 4));
    uart_put_hex_nibble((uint8_t)(v & 0x0FU));
}

static int parse_hex_u32(const char *s, uint32_t *out)
{
    if (s == NULL || *s == '\0') {
        return -1;
    }
    char *end = NULL;
    unsigned long v = strtoul(s, &end, 16);
    if (end == s || *end != '\0') {
        return -1;
    }
    *out = (uint32_t)v;
    return 0;
}

static void cmd_dump_memory(uint32_t addr, uint32_t len)
{
    if (len == 0U) {
        uart_puts("ERR: len=0\r\n");
        return;
    }
    if (len > 4096U) {
        len = 4096U;
        uart_puts("WARN: len capped to 4096\r\n");
    }
    const uint8_t *p = (const uint8_t *)(uintptr_t)addr;
    for (uint32_t off = 0U; off < len; off += DUMP_LINE_BYTES) {
        uart_put_hex_u32(addr + off);
        uart_puts(": ");
        uint32_t n = DUMP_LINE_BYTES;
        if (off + n > len) {
            n = len - off;
        }
        for (uint32_t i = 0U; i < n; ++i) {
            uart_put_hex_u8(p[off + i]);
            platform_uart_tx_byte((uint8_t)' ');
        }
        uart_puts("\r\n");
    }
}

static void cmd_read_flash(uint32_t addr, uint32_t len)
{
    static uint8_t chunk[FLASH_READ_CHUNK];
    if (len == 0U) {
        uart_puts("ERR: len=0\r\n");
        return;
    }
    if (len > 65536U) {
        len = 65536U;
        uart_puts("WARN: len capped to 65536\r\n");
    }
    for (uint32_t off = 0U; off < len; ) {
        uint32_t take = FLASH_READ_CHUNK;
        if (off + take > len) {
            take = len - off;
        }
        if (platform_flash_read(addr + off, chunk, take) != 0) {
            uart_puts("ERR: flash_read failed\r\n");
            return;
        }
        for (uint32_t i = 0U; i < take; ++i) {
            if ((i % DUMP_LINE_BYTES) == 0U) {
                uart_put_hex_u32(addr + off + i);
                uart_puts(": ");
            }
            uart_put_hex_u8(chunk[i]);
            if ((i % DUMP_LINE_BYTES) == (DUMP_LINE_BYTES - 1U) || (i + 1U) == take) {
                uart_puts("\r\n");
            } else {
                platform_uart_tx_byte((uint8_t)' ');
            }
        }
        off += take;
    }
}

static void cmd_get_config(void)
{
    sensor_config_t cfg;
    if (platform_get_config(&cfg) != 0) {
        uart_puts("ERR: get_config failed\r\n");
        return;
    }
    uart_puts("device_id: ");
    uart_put_hex_u32(cfg.device_id);
    uart_puts("\r\nsample_period_ms: ");
    char num[12];
    snprintf(num, sizeof(num), "%lu", (unsigned long)cfg.sample_period_ms);
    uart_puts(num);
    uart_puts("\r\nflags: ");
    uart_put_hex_u32(cfg.flags);
    uart_puts("\r\n");
}

static void process_line(void)
{
    char *argv[8];
    int argc = 0;
    char *save = NULL;
    char *tok = strtok_r(line_buf, " \t\r\n", &save);
    while (tok != NULL && argc < (int)(sizeof(argv) / sizeof(argv[0]))) {
        argv[argc++] = tok;
        tok = strtok_r(NULL, " \t\r\n", &save);
    }
    if (argc == 0) {
        return;
    }
    if (strcmp(argv[0], "dump_memory") == 0) {
        if (argc < 3) {
            uart_puts("USAGE: dump_memory <addr_hex> <len_hex>\r\n");
            return;
        }
        uint32_t a, l;
        if (parse_hex_u32(argv[1], &a) != 0 || parse_hex_u32(argv[2], &l) != 0) {
            uart_puts("ERR: bad hex args\r\n");
            return;
        }
        cmd_dump_memory(a, l);
    } else if (strcmp(argv[0], "read_flash") == 0) {
        if (argc < 3) {
            uart_puts("USAGE: read_flash <addr_hex> <len_hex>\r\n");
            return;
        }
        uint32_t a, l;
        if (parse_hex_u32(argv[1], &a) != 0 || parse_hex_u32(argv[2], &l) != 0) {
            uart_puts("ERR: bad hex args\r\n");
            return;
        }
        cmd_read_flash(a, l);
    } else if (strcmp(argv[0], "get_config") == 0) {
        cmd_get_config();
    } else if (strcmp(argv[0], "help") == 0) {
        uart_puts("dump_memory <addr_hex> <len_hex>\r\n");
        uart_puts("read_flash <addr_hex> <len_hex>\r\n");
        uart_puts("get_config\r\n");
        uart_puts("help\r\n");
    } else {
        uart_puts("ERR: unknown command\r\n");
    }
}

void diagnostic_console_init(void)
{
    line_len = 0U;
    platform_uart_init(115200U);
    platform_jtag_debug_pins_init();
    uart_puts("\r\nDIAG shell ready. Type 'help'.\r\n");
}

void diagnostic_console_poll(void)
{
    int c = platform_uart_rx_try();
    if (c < 0) {
        return;
    }
    uint8_t b = (uint8_t)c;
    if (b == '\r' || b == '\n') {
        if (line_len > 0U) {
            line_buf[line_len] = '\0';
            process_line();
        }
        line_len = 0U;
        uart_puts("\r\n> ");
        return;
    }
    if (b == 0x08U || b == 0x7FU) {
        if (line_len > 0U) {
            --line_len;
            uart_puts("\b \b");
        }
        return;
    }
    if (line_len < (SHELL_LINE_MAX - 1U)) {
        line_buf[line_len++] = (char)b;
        platform_uart_tx_byte(b);
    }
}

#include "diagnostic_console.h"
#include "platform_hw.h"

int main(void)
{
    diagnostic_console_init();
    for (;;) {
        diagnostic_console_poll();
    }
    return 0;
}

#include "platform_hw.h"
#include <stdint.h>
#include <string.h>

#if defined(STM32F407xx) || defined(USE_STM32_HAL)

#include "stm32f4xx_hal.h"

#ifndef DIAG_UART
#define DIAG_UART        USART2
#define DIAG_UART_IRQn   USART2_IRQn
#define DIAG_UART_CLK()  __HAL_RCC_USART2_CLK_ENABLE()
#define DIAG_GPIO_AF     GPIO_AF7_USART2
#endif

static UART_HandleTypeDef huart_diag;

void HAL_UART_MspInit(UART_HandleTypeDef *huart)
{
    if (huart->Instance != DIAG_UART) {
        return;
    }
    GPIO_InitTypeDef g = {0};
    __HAL_RCC_GPIOA_CLK_ENABLE();
    g.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    g.Mode = GPIO_MODE_AF_PP;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    g.Alternate = DIAG_GPIO_AF;
    HAL_GPIO_Init(GPIOA, &g);
}

void platform_uart_init(uint32_t baud)
{
    HAL_Init();
    DIAG_UART_CLK();
    huart_diag.Instance = DIAG_UART;
    huart_diag.Init.BaudRate = baud;
    huart_diag.Init.WordLength = UART_WORDLENGTH_8B;
    huart_diag.Init.StopBits = UART_STOPBITS_1;
    huart_diag.Init.Parity = UART_PARITY_NONE;
    huart_diag.Init.Mode = UART_MODE_TX_RX;
    huart_diag.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart_diag.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart_diag);
    __HAL_UART_ENABLE_IT(&huart_diag, UART_IT_RXNE);
    HAL_NVIC_SetPriority(DIAG_UART_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(DIAG_UART_IRQn);
}

static volatile uint8_t rx_fifo[256];
static volatile uint32_t rx_head;
static volatile uint32_t rx_tail;

void USART2_IRQHandler(void)
{
    if (__HAL_UART_GET_FLAG(&huart_diag, UART_FLAG_RXNE)) {
        uint8_t v = (uint8_t)(huart_diag.Instance->DR & 0xFFU);
        uint32_t next = (rx_head + 1U) % (uint32_t)sizeof(rx_fifo);
        if (next != rx_tail) {
            rx_fifo[rx_head] = v;
            rx_head = next;
        }
    }
}

void platform_uart_tx_byte(uint8_t b)
{
    HAL_UART_Transmit(&huart_diag, &b, 1U, 100U);
}

int platform_uart_rx_try(void)
{
    if (rx_tail == rx_head) {
        return -1;
    }
    uint8_t v = rx_fifo[rx_tail];
    rx_tail = (rx_tail + 1U) % (uint32_t)sizeof(rx_fifo);
    return (int)v;
}

int platform_flash_read(uint32_t addr, uint8_t *buf, uint32_t len)
{
    memcpy(buf, (const void *)(uintptr_t)addr, len);
    return 0;
}

static const sensor_config_t g_cfg = {
    .device_id = 0xA0010001U,
    .sample_period_ms = 1000U,
    .flags = 0x00000003U,
};

int platform_get_config(sensor_config_t *out)
{
    if (out == NULL) {
        return -1;
    }
    *out = g_cfg;
    return 0;
}

void platform_jtag_debug_pins_init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    GPIO_InitTypeDef g = {0};
    g.Mode = GPIO_MODE_AF_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    g.Alternate = GPIO_AF0_SWJ;
    g.Pin = GPIO_PIN_13 | GPIO_PIN_14 | GPIO_PIN_15;
    HAL_GPIO_Init(GPIOA, &g);
    g.Pin = GPIO_PIN_3 | GPIO_PIN_4;
    HAL_GPIO_Init(GPIOB, &g);
}

#else

#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

void platform_uart_init(uint32_t baud)
{
    (void)baud;
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    (void)fcntl(STDIN_FILENO, F_SETFL, fcntl(STDIN_FILENO, F_GETFL, 0) | O_NONBLOCK);
}

void platform_uart_tx_byte(uint8_t b)
{
    putchar((int)b);
    fflush(stdout);
}

int platform_uart_rx_try(void)
{
    unsigned char c;
    ssize_t n = read(STDIN_FILENO, &c, 1);
    if (n == 1) {
        return (int)c;
    }
    if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
        return -1;
    }
    return -1;
}

int platform_flash_read(uint32_t addr, uint8_t *buf, uint32_t len)
{
    static uint8_t fake[65536];
    for (uint32_t i = 0U; i < len; ++i) {
        buf[i] = fake[(addr + i) % sizeof(fake)];
    }
    return 0;
}

static const sensor_config_t g_cfg = {
    .device_id = 0xA0010001U,
    .sample_period_ms = 1000U,
    .flags = 0x00000003U,
};

int platform_get_config(sensor_config_t *out)
{
    if (out == NULL) {
        return -1;
    }
    *out = g_cfg;
    return 0;
}

void platform_jtag_debug_pins_init(void)
{
}

#endif