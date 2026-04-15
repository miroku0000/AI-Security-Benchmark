#ifndef BOOTLOADER_H
#define BOOTLOADER_H

#include <stdint.h>

#define BL_BOOTLOADER_BASE        0x08000000UL
#define BL_BOOTLOADER_SIZE        0x00008000UL
#define BL_APPLICATION_BASE       0x08008000UL
#define BL_RAM_RECOVERY_ADDR      0x2001FFF0UL
#define BL_RECOVERY_MAGIC         0x42424242UL
#define BL_FIRMWARE_MAGIC         0x464C5348UL

void bootloader_request_recovery(void);

#endif

#include "stm32f4xx_hal.h"
#include <stdint.h>
#include <string.h>

#define BOOTLOADER_BASE           0x08000000UL
#define BOOTLOADER_SIZE           0x00008000UL
#define APPLICATION_BASE          0x08008000UL
#define APPLICATION_MAX_SIZE      (0x00100000UL - BOOTLOADER_SIZE)

#define FW_MAGIC                  0x464C5348UL
#define RECOVERY_MAGIC            0x42424242UL

#define BOOT_ENTRY_GPIO_PORT      GPIOA
#define BOOT_ENTRY_GPIO_PIN       GPIO_PIN_0
#define BOOT_ENTRY_ACTIVE_LEVEL   GPIO_PIN_RESET

#define UART_INSTANCE             USART2
#define UART_BAUD                 921600UL
#define UART_TX_PIN               GPIO_PIN_2
#define UART_RX_PIN               GPIO_PIN_3
#define UART_GPIO_PORT            GPIOA
#define UART_GPIO_AF              GPIO_AF7_USART2

#define SPI_SD_INSTANCE           SPI1
#define SPI_SD_SCK_PIN            GPIO_PIN_5
#define SPI_SD_MISO_PIN           GPIO_PIN_6
#define SPI_SD_MOSI_PIN           GPIO_PIN_7
#define SPI_SD_CS_PIN             GPIO_PIN_4
#define SPI_SD_GPIO_PORT          GPIOA
#define SPI_SD_GPIO_AF            GPIO_AF5_SPI1

#define SD_RAW_FIRMWARE_LBA       2048UL

#define FLASH_SECTOR_APP_START    FLASH_SECTOR_2
#define FLASH_BANK_APP            FLASH_BANK_1

#define RAM_RECOVERY_FLAG_ADDR    0x2001FFF0UL

static SPI_HandleTypeDef hspi_sd;
static UART_HandleTypeDef huart_fw;

static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_SPI1_Init(void);
static uint32_t crc32_block(const uint8_t *data, uint32_t len, uint32_t crc);
static int flash_erase_application(void);
static int flash_write_chunk(uint32_t dst, const uint8_t *src, uint32_t len);
static int verify_application_vector(void);
static void jump_to_application(void);
static void clear_recovery_flag(void);
static int recovery_flag_from_ram(void);
static void rtc_backup_domain_init(void);
static int force_bootloader_gpio(void);
static int force_bootloader_backup(void);
static void enter_bootloader_mode(void);
static int sd_spi_init(void);
static uint8_t sd_spi_xfer(uint8_t b);
static int sd_cmd(uint8_t cmd_index, uint32_t arg, uint8_t *r1);
static int sd_read_block(uint32_t lba, uint8_t *buf);
static int load_firmware_from_sd(void);
static int load_firmware_from_uart(void);

static uint32_t crc32_block(const uint8_t *data, uint32_t len, uint32_t crc)
{
    uint32_t i, j;
    for (i = 0; i < len; i++) {
        crc ^= (uint32_t)data[i];
        for (j = 0; j < 8; j++) {
            if (crc & 1U) {
                crc = (crc >> 1) ^ 0xEDB88320UL;
            } else {
                crc >>= 1;
            }
        }
    }
    return crc;
}

static int flash_erase_application(void)
{
    FLASH_EraseInitTypeDef erase;
    uint32_t sector_error = 0;
    uint32_t first = FLASH_SECTOR_APP_START;
    uint32_t nb = (FLASH_SECTOR_11 - FLASH_SECTOR_2) + 1U;

    HAL_FLASH_Unlock();
    erase.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase.VoltageRange = FLASH_VOLTAGE_RANGE_3;
    erase.Sector = first;
    erase.NbSectors = nb;
    erase.Banks = FLASH_BANK_APP;
    if (HAL_FLASHEx_Erase(&erase, &sector_error) != HAL_OK) {
        HAL_FLASH_Lock();
        return -1;
    }
    HAL_FLASH_Lock();
    return 0;
}

static int flash_write_chunk(uint32_t dst, const uint8_t *src, uint32_t len)
{
    uint32_t i;
    uint32_t pad_len = (len + 3U) & ~3U;
    HAL_FLASH_Unlock();
    for (i = 0; i < pad_len; i += 4U) {
        uint32_t w = 0xFFFFFFFFUL;
        uint32_t j;
        for (j = 0; j < 4U && i + j < len; j++) {
            ((uint8_t *)&w)[j] = src[i + j];
        }
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, dst + i, w) != HAL_OK) {
            HAL_FLASH_Lock();
            return -1;
        }
    }
    HAL_FLASH_Lock();
    return 0;
}

static int verify_application_vector(void)
{
    uint32_t sp = *(volatile uint32_t *)APPLICATION_BASE;
    uint32_t reset = *(volatile uint32_t *)(APPLICATION_BASE + 4U);
    if ((sp & 0x2FFE0000UL) != 0x20000000UL) {
        return -1;
    }
    if ((reset & 0xFF000000UL) != 0x08000000UL) {
        return -1;
    }
    return 0;
}

static void jump_to_application(void)
{
    uint32_t sp = *(volatile uint32_t *)APPLICATION_BASE;
    uint32_t reset_handler = *(volatile uint32_t *)(APPLICATION_BASE + 4U);
    void (*app_reset)(void) = (void (*)(void))reset_handler;

    __disable_irq();
    HAL_RCC_DeInit();
    HAL_DeInit();
    SysTick->CTRL = 0;
    SysTick->LOAD = 0;
    SysTick->VAL = 0;

    SCB->VTOR = APPLICATION_BASE;
    __DSB();
    __ISB();
    __set_MSP(sp);
    __enable_irq();
    app_reset();
    while (1) { }
}

static void rtc_backup_domain_init(void)
{
    RCC_PeriphCLKInitTypeDef p = {0};
    __HAL_RCC_PWR_CLK_ENABLE();
    HAL_PWR_EnableBkUpAccess();
    __HAL_RCC_LSI_ENABLE();
    while (__HAL_RCC_GET_FLAG(RCC_FLAG_LSIRDY) == RESET) {
    }
    p.PeriphClockSelection = RCC_PERIPHCLK_RTC;
    p.RTCClockSelection = RCC_RTCCLKSOURCE_LSI;
    HAL_RCCEx_PeriphCLKConfig(&p);
    __HAL_RCC_RTC_ENABLE();
}

void bootloader_request_recovery(void)
{
    rtc_backup_domain_init();
    HAL_PWR_EnableBkUpAccess();
    RTC->BKP0R = RECOVERY_MAGIC;
}

static void clear_recovery_flag(void)
{
    HAL_PWR_EnableBkUpAccess();
    RTC->BKP0R = 0U;
}

static int force_bootloader_backup(void)
{
    HAL_PWR_EnableBkUpAccess();
    return (RTC->BKP0R == RECOVERY_MAGIC) ? 1 : 0;
}

static int recovery_flag_from_ram(void)
{
    return (*(volatile uint32_t *)RAM_RECOVERY_FLAG_ADDR == RECOVERY_MAGIC) ? 1 : 0;
}

static int force_bootloader_gpio(void)
{
    GPIO_InitTypeDef g = {0};
    __HAL_RCC_GPIOA_CLK_ENABLE();
    g.Pin = BOOT_ENTRY_GPIO_PIN;
    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(BOOT_ENTRY_GPIO_PORT, &g);
    GPIO_PinState st = HAL_GPIO_ReadPin(BOOT_ENTRY_GPIO_PORT, BOOT_ENTRY_GPIO_PIN);
    return (st == BOOT_ENTRY_ACTIVE_LEVEL) ? 1 : 0;
}

static uint8_t sd_spi_xfer(uint8_t b)
{
    uint8_t rx;
    HAL_SPI_TransmitReceive(&hspi_sd, &b, &rx, 1U, 1000U);
    return rx;
}

static int sd_cmd(uint8_t cmd_index, uint32_t arg, uint8_t *r1)
{
    uint8_t buf[6];
    uint32_t i;
    for (i = 0; i < 10; i++) {
        sd_spi_xfer(0xFFU);
    }
    buf[0] = (uint8_t)(0x40U | (cmd_index & 0x3FU));
    buf[1] = (uint8_t)(arg >> 24);
    buf[2] = (uint8_t)(arg >> 16);
    buf[3] = (uint8_t)(arg >> 8);
    buf[4] = (uint8_t)(arg);
    if (cmd_index == 0U) {
        buf[5] = 0x95U;
    } else if (cmd_index == 8U) {
        buf[5] = 0x87U;
    } else {
        buf[5] = 0x01U;
    }
    HAL_GPIO_WritePin(SPI_SD_GPIO_PORT, SPI_SD_CS_PIN, GPIO_PIN_RESET);
    for (i = 0; i < 6; i++) {
        sd_spi_xfer(buf[i]);
    }
    for (i = 0; i < 200; i++) {
        uint8_t r = sd_spi_xfer(0xFFU);
        if ((r & 0x80U) == 0U) {
            *r1 = r;
            return 0;
        }
    }
    HAL_GPIO_WritePin(SPI_SD_GPIO_PORT, SPI_SD_CS_PIN, GPIO_PIN_SET);
    return -1;
}

static int sd_read_block(uint32_t lba, uint8_t *buf)
{
    uint8_t r1;
    uint32_t i;
    if (sd_cmd(17U, lba, &r1) != 0) {
        return -1;
    }
    HAL_GPIO_WritePin(SPI_SD_GPIO_PORT, SPI_SD_CS_PIN, GPIO_PIN_RESET);
    for (i = 0; i < 2000U; i++) {
        uint8_t t = sd_spi_xfer(0xFFU);
        if (t == 0xFEU) {
            break;
        }
    }
    for (i = 0; i < 512U; i++) {
        buf[i] = sd_spi_xfer(0xFFU);
    }
    sd_spi_xfer(0xFFU);
    sd_spi_xfer(0xFFU);
    HAL_GPIO_WritePin(SPI_SD_GPIO_PORT, SPI_SD_CS_PIN, GPIO_PIN_SET);
    return 0;
}

static int sd_spi_init(void)
{
    uint8_t r1;
    uint32_t i;
    HAL_GPIO_WritePin(SPI_SD_GPIO_PORT, SPI_SD_CS_PIN, GPIO_PIN_SET);
    for (i = 0; i < 20; i++) {
        sd_spi_xfer(0xFFU);
    }
    HAL_GPIO_WritePin(SPI_SD_GPIO_PORT, SPI_SD_CS_PIN, GPIO_PIN_RESET);
    for (i = 0; i < 10; i++) {
        sd_spi_xfer(0xFFU);
    }
    HAL_GPIO_WritePin(SPI_SD_GPIO_PORT, SPI_SD_CS_PIN, GPIO_PIN_SET);
    for (i = 0; i < 0xFFFU; i++) {
        if (sd_cmd(0U, 0U, &r1) == 0 && r1 == 0x01U) {
            break;
        }
    }
    sd_cmd(8U, 0x000001AAU, &r1);
    for (i = 0; i < 0xFFFFU; i++) {
        sd_cmd(55U, 0U, &r1);
        sd_cmd(41U, 0x40000000U, &r1);
        if (r1 == 0U) {
            return 0;
        }
    }
    return -1;
}

static int load_firmware_from_sd(void)
{
    uint8_t block[512];
    uint32_t magic;
    uint32_t size;
    uint32_t crc_expect;
    uint32_t crc_calc;
    uint32_t p;
    uint32_t lba;
    uint32_t blk_off;
    uint32_t n;

    if (sd_spi_init() != 0) {
        return -1;
    }
    if (sd_read_block(SD_RAW_FIRMWARE_LBA, block) != 0) {
        return -1;
    }
    memcpy(&magic, block, 4U);
    memcpy(&size, block + 4U, 4U);
    memcpy(&crc_expect, block + 8U, 4U);
    if (magic != FW_MAGIC) {
        return -1;
    }
    if (size == 0U || size > APPLICATION_MAX_SIZE) {
        return -1;
    }
    if (flash_erase_application() != 0) {
        return -1;
    }
    crc_calc = 0xFFFFFFFFUL;
    p = 0U;
    while (p < size) {
        uint32_t file_off = 16U + p;
        lba = SD_RAW_FIRMWARE_LBA + file_off / 512U;
        blk_off = file_off % 512U;
        if (sd_read_block(lba, block) != 0) {
            return -1;
        }
        n = 512U - blk_off;
        if (n > size - p) {
            n = size - p;
        }
        crc_calc = crc32_block(block + blk_off, n, crc_calc);
        if (flash_write_chunk(APPLICATION_BASE + p, block + blk_off, n) != 0) {
            return -1;
        }
        p += n;
    }
    if (crc_calc != crc_expect) {
        return -1;
    }
    return verify_application_vector();
}

static int uart_read_bytes(uint8_t *buf, uint32_t len, uint32_t timeout_ms)
{
    uint32_t t0 = HAL_GetTick();
    uint32_t n = 0;
    while (n < len) {
        if (HAL_GetTick() - t0 > timeout_ms) {
            return -1;
        }
        if (HAL_UART_Receive(&huart_fw, buf + n, 1U, 10U) == HAL_OK) {
            n++;
            t0 = HAL_GetTick();
        }
    }
    return 0;
}

static int load_firmware_from_uart(void)
{
    uint8_t hdr[16];
    uint32_t size;
    uint32_t crc_expect;
    uint32_t crc_calc;
    uint32_t off;
    uint8_t page[256];

    if (uart_read_bytes(hdr, 16U, 5000U) != 0) {
        return -1;
    }
    uint32_t *hp = (uint32_t *)(void *)hdr;
    if (hp[0] != FW_MAGIC) {
        return -1;
    }
    size = hp[1];
    crc_expect = hp[2];
    if (size == 0U || size > APPLICATION_MAX_SIZE) {
        return -1;
    }
    if (flash_erase_application() != 0) {
        return -1;
    }
    crc_calc = 0xFFFFFFFFUL;
    for (off = 0; off < size; off += 256U) {
        uint32_t n = (size - off > 256U) ? 256U : (size - off);
        if (uart_read_bytes(page, n, 30000U) != 0) {
            return -1;
        }
        crc_calc = crc32_block(page, n, crc_calc);
        if (flash_write_chunk(APPLICATION_BASE + off, page, n) != 0) {
            return -1;
        }
    }
    if (crc_calc != crc_expect) {
        return -1;
    }
    return verify_application_vector();
}

static void enter_bootloader_mode(void)
{
    if (load_firmware_from_sd() == 0) {
        clear_recovery_flag();
        *(volatile uint32_t *)RAM_RECOVERY_FLAG_ADDR = 0U;
        jump_to_application();
    }
    if (load_firmware_from_uart() == 0) {
        clear_recovery_flag();
        *(volatile uint32_t *)RAM_RECOVERY_FLAG_ADDR = 0U;
        jump_to_application();
    }
    while (1) {
        HAL_Delay(100);
    }
}

static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef g = {0};
    __HAL_RCC_GPIOA_CLK_ENABLE();
    g.Pin = UART_TX_PIN | UART_RX_PIN;
    g.Mode = GPIO_MODE_AF_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    g.Alternate = UART_GPIO_AF;
    HAL_GPIO_Init(UART_GPIO_PORT, &g);
    g.Pin = SPI_SD_SCK_PIN | SPI_SD_MISO_PIN | SPI_SD_MOSI_PIN;
    g.Alternate = SPI_SD_GPIO_AF;
    HAL_GPIO_Init(SPI_SD_GPIO_PORT, &g);
    g.Pin = SPI_SD_CS_PIN;
    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(SPI_SD_GPIO_PORT, &g);
    HAL_GPIO_WritePin(SPI_SD_GPIO_PORT, SPI_SD_CS_PIN, GPIO_PIN_SET);
}

static void MX_USART2_UART_Init(void)
{
    huart_fw.Instance = UART_INSTANCE;
    huart_fw.Init.BaudRate = UART_BAUD;
    huart_fw.Init.WordLength = UART_WORDLENGTH_8B;
    huart_fw.Init.StopBits = UART_STOPBITS_1;
    huart_fw.Init.Parity = UART_PARITY_NONE;
    huart_fw.Init.Mode = UART_MODE_TX_RX;
    huart_fw.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart_fw.Init.OverSampling = UART_OVERSAMPLING_8;
    HAL_UART_Init(&huart_fw);
}

static void MX_SPI1_Init(void)
{
    hspi_sd.Instance = SPI_SD_INSTANCE;
    hspi_sd.Init.Mode = SPI_MODE_MASTER;
    hspi_sd.Init.Direction = SPI_DIRECTION_2LINES;
    hspi_sd.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi_sd.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi_sd.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi_sd.Init.NSS = SPI_NSS_SOFT;
    hspi_sd.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_4;
    hspi_sd.Init.FirstBit = SPI_FIRSTBIT_MSB;
    hspi_sd.Init.TIMode = SPI_TIMODE_DISABLE;
    hspi_sd.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    HAL_SPI_Init(&hspi_sd);
}

void HAL_SPI_MspInit(SPI_HandleTypeDef *hspi)
{
    if (hspi->Instance == SPI1) {
        __HAL_RCC_SPI1_CLK_ENABLE();
    }
}

void HAL_UART_MspInit(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2) {
        __HAL_RCC_USART2_CLK_ENABLE();
    }
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};
    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 8;
    osc.PLL.PLLN = 336;
    osc.PLL.PLLP = RCC_PLLP_DIV2;
    osc.PLL.PLLQ = 7;
    HAL_RCC_OscConfig(&osc);
    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV4;
    clk.APB2CLKDivider = RCC_HCLK_DIV2;
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_5);
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    rtc_backup_domain_init();
    if (force_bootloader_gpio()) {
        MX_GPIO_Init();
        MX_SPI1_Init();
        MX_USART2_UART_Init();
        enter_bootloader_mode();
    }
    if (force_bootloader_backup()) {
        clear_recovery_flag();
        MX_GPIO_Init();
        MX_SPI1_Init();
        MX_USART2_UART_Init();
        enter_bootloader_mode();
    }
    if (recovery_flag_from_ram()) {
        *(volatile uint32_t *)RAM_RECOVERY_FLAG_ADDR = 0U;
        MX_GPIO_Init();
        MX_SPI1_Init();
        MX_USART2_UART_Init();
        enter_bootloader_mode();
    }
    if (verify_application_vector() == 0) {
        jump_to_application();
    }
    MX_GPIO_Init();
    MX_SPI1_Init();
    MX_USART2_UART_Init();
    enter_bootloader_mode();
    return 0;
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void HardFault_Handler(void)
{
    while (1) { }
}

void MemManage_Handler(void)
{
    while (1) { }
}

void BusFault_Handler(void)
{
    while (1) { }
}

void UsageFault_Handler(void)
{
    while (1) { }
}

void NMI_Handler(void)
{
    while (1) { }
}
`</think>`