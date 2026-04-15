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
