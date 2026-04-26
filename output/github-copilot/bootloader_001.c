#include "stm32f4xx_hal.h"
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#define APP_ADDRESS                 0x08010000UL
#define FLASH_END_ADDRESS           0x080FFFFFUL
#define APP_MAX_SIZE                (FLASH_END_ADDRESS - APP_ADDRESS + 1UL)

#define SRAM_START                  0x20000000UL
#define SRAM_END                    0x2001FFFFUL

#define BOOT_FLAG_ADDRESS           0x40024000UL
#define BOOT_FLAG_MAGIC             0xB00720ADUL

#define UPDATE_MAGIC                0x54445055UL

#define SD_UPDATE_SLOT_LBA          2048UL
#define SD_BLOCK_SIZE               512UL

#define UART_BAUD_RATE              921600UL
#define UART_PROBE_TIMEOUT_MS       250UL
#define UART_TRANSFER_TIMEOUT_MS    5000UL

#define BOOT_GPIO_PORT              GPIOC
#define BOOT_GPIO_PIN               GPIO_PIN_13

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint32_t image_size;
    uint32_t image_crc32;
    uint32_t reserved;
} update_header_t;

UART_HandleTypeDef huart2;
SD_HandleTypeDef hsd;

static uint8_t sd_sector[SD_BLOCK_SIZE] __attribute__((aligned(4)));
static uint8_t uart_buffer[1024] __attribute__((aligned(4)));

static const uint32_t crc32_nibble_table[16] = {
    0x00000000UL, 0x1DB71064UL, 0x3B6E20C8UL, 0x26D930ACUL,
    0x76DC4190UL, 0x6B6B51F4UL, 0x4DB26158UL, 0x5005713CUL,
    0xEDB88320UL, 0xF00F9344UL, 0xD6D6A3E8UL, 0xCB61B38CUL,
    0x9B64C2B0UL, 0x86D3D2D4UL, 0xA00AE278UL, 0xBDBDF21CUL
};

static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_SDIO_SD_Init(void);
static void Error_Handler(void);

static void uart_write(const void *data, uint16_t length);
static void uart_write_str(const char *str);

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, uint32_t length);
static uint32_t crc32_memory(const uint8_t *data, uint32_t length);

static bool boot_pin_asserted(void);
static bool take_boot_request_flag(void);
static bool application_is_valid(void);
static void jump_to_application(void) __attribute__((noreturn));

static bool image_size_is_valid(uint32_t image_size);
static uint32_t flash_sector_for_address(uint32_t address);
static bool flash_begin_image(uint32_t image_size);
static bool flash_program_bytes(uint32_t address, const uint8_t *data, uint32_t length);

static bool wait_for_sd_transfer(uint32_t timeout_ms);
static bool sd_init_card(void);
static bool sd_read_sector(uint32_t lba, uint8_t *buffer);
static bool sd_write_sector(uint32_t lba, const uint8_t *buffer);
static bool clear_sd_update_slot(void);

static bool process_sd_update(void);
static bool process_uart_update(uint32_t header_timeout_ms, bool announce_errors);

static void system_reset(void);

int main(void)
{
    bool stay_in_bootloader;

    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART2_UART_Init();
    MX_SDIO_SD_Init();

    stay_in_bootloader = take_boot_request_flag() || boot_pin_asserted() || !application_is_valid();

    if (process_sd_update()) {
        system_reset();
    }

    if (!stay_in_bootloader) {
        if (process_uart_update(UART_PROBE_TIMEOUT_MS, false)) {
            system_reset();
        }
        jump_to_application();
    }

    uart_write_str("BOOT\r\n");

    while (1) {
        if (process_sd_update()) {
            system_reset();
        }
        if (process_uart_update(200U, true)) {
            system_reset();
        }
    }
}

static void uart_write(const void *data, uint16_t length)
{
    (void)HAL_UART_Transmit(&huart2, (uint8_t *)data, length, 1000U);
}

static void uart_write_str(const char *str)
{
    uart_write(str, (uint16_t)strlen(str));
}

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, uint32_t length)
{
    uint32_t i;

    for (i = 0U; i < length; ++i) {
        crc ^= data[i];
        crc = (crc >> 4) ^ crc32_nibble_table[crc & 0x0FU];
        crc = (crc >> 4) ^ crc32_nibble_table[crc & 0x0FU];
    }

    return crc;
}

static uint32_t crc32_memory(const uint8_t *data, uint32_t length)
{
    return crc32_update(0xFFFFFFFFUL, data, length) ^ 0xFFFFFFFFUL;
}

static bool boot_pin_asserted(void)
{
    return HAL_GPIO_ReadPin(BOOT_GPIO_PORT, BOOT_GPIO_PIN) == GPIO_PIN_RESET;
}

static bool take_boot_request_flag(void)
{
    volatile uint32_t *flag;
    bool requested;

    __HAL_RCC_PWR_CLK_ENABLE();
    HAL_PWR_EnableBkUpAccess();
    __HAL_RCC_BKPSRAM_CLK_ENABLE();

    flag = (volatile uint32_t *)BOOT_FLAG_ADDRESS;
    requested = (*flag == BOOT_FLAG_MAGIC);
    *flag = 0U;
    __DSB();
    __ISB();

    return requested;
}

static bool application_is_valid(void)
{
    uint32_t initial_sp = *(__IO uint32_t *)APP_ADDRESS;
    uint32_t reset_handler = *(__IO uint32_t *)(APP_ADDRESS + 4U);
    uint32_t reset_target = reset_handler & ~1UL;

    if ((initial_sp < SRAM_START) || (initial_sp > (SRAM_END + 1UL))) {
        return false;
    }

    if ((reset_handler & 1UL) == 0U) {
        return false;
    }

    if ((reset_target < APP_ADDRESS) || (reset_target > FLASH_END_ADDRESS)) {
        return false;
    }

    return true;
}

static void jump_to_application(void)
{
    uint32_t app_stack = *(__IO uint32_t *)APP_ADDRESS;
    uint32_t app_reset = *(__IO uint32_t *)(APP_ADDRESS + 4U);
    void (*app_entry)(void) = (void (*)(void))app_reset;
    uint32_t i;

    HAL_SD_DeInit(&hsd);
    HAL_UART_DeInit(&huart2);
    HAL_RCC_DeInit();
    HAL_DeInit();

    __disable_irq();

    SysTick->CTRL = 0U;
    SysTick->LOAD = 0U;
    SysTick->VAL = 0U;

    for (i = 0U; i < 8U; ++i) {
        NVIC->ICER[i] = 0xFFFFFFFFUL;
        NVIC->ICPR[i] = 0xFFFFFFFFUL;
    }

    SCB->VTOR = APP_ADDRESS;
    __DSB();
    __ISB();
    __set_MSP(app_stack);
    app_entry();

    while (1) {
    }
}

static bool image_size_is_valid(uint32_t image_size)
{
    return (image_size > 0U) && (image_size <= APP_MAX_SIZE);
}

static uint32_t flash_sector_for_address(uint32_t address)
{
    if (address < 0x08004000UL) return FLASH_SECTOR_0;
    if (address < 0x08008000UL) return FLASH_SECTOR_1;
    if (address < 0x0800C000UL) return FLASH_SECTOR_2;
    if (address < 0x08010000UL) return FLASH_SECTOR_3;
    if (address < 0x08020000UL) return FLASH_SECTOR_4;
    if (address < 0x08040000UL) return FLASH_SECTOR_5;
    if (address < 0x08060000UL) return FLASH_SECTOR_6;
    if (address < 0x08080000UL) return FLASH_SECTOR_7;
    if (address < 0x080A0000UL) return FLASH_SECTOR_8;
    if (address < 0x080C0000UL) return FLASH_SECTOR_9;
    if (address < 0x080E0000UL) return FLASH_SECTOR_10;
    return FLASH_SECTOR_11;
}

static bool flash_begin_image(uint32_t image_size)
{
    FLASH_EraseInitTypeDef erase_init;
    uint32_t sector_error = 0U;
    uint32_t first_sector = flash_sector_for_address(APP_ADDRESS);
    uint32_t last_sector = flash_sector_for_address(APP_ADDRESS + image_size - 1U);

    if (!image_size_is_valid(image_size)) {
        return false;
    }

    if (HAL_FLASH_Unlock() != HAL_OK) {
        return false;
    }

    __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_EOP | FLASH_FLAG_OPERR | FLASH_FLAG_WRPERR |
                           FLASH_FLAG_PGAERR | FLASH_FLAG_PGPERR | FLASH_FLAG_PGSERR);

    memset(&erase_init, 0, sizeof(erase_init));
    erase_init.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase_init.VoltageRange = FLASH_VOLTAGE_RANGE_3;
    erase_init.Sector = first_sector;
    erase_init.NbSectors = (last_sector - first_sector) + 1U;

    if (HAL_FLASHEx_Erase(&erase_init, &sector_error) != HAL_OK) {
        HAL_FLASH_Lock();
        return false;
    }

    return true;
}

static bool flash_program_bytes(uint32_t address, const uint8_t *data, uint32_t length)
{
    uint32_t offset = 0U;

    while (offset < length) {
        uint32_t word = 0xFFFFFFFFUL;
        uint32_t chunk = (length - offset >= 4U) ? 4U : (length - offset);

        memcpy(&word, &data[offset], chunk);

        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, address + offset, word) != HAL_OK) {
            return false;
        }

        offset += chunk;
    }

    return true;
}

static bool wait_for_sd_transfer(uint32_t timeout_ms)
{
    uint32_t start = HAL_GetTick();

    while ((HAL_GetTick() - start) < timeout_ms) {
        if (HAL_SD_GetCardState(&hsd) == HAL_SD_CARD_TRANSFER) {
            return true;
        }
    }

    return false;
}

static bool sd_init_card(void)
{
    if (HAL_SD_Init(&hsd) != HAL_OK) {
        return false;
    }

    if (HAL_SD_ConfigWideBusOperation(&hsd, SDIO_BUS_WIDE_4B) != HAL_OK) {
        return false;
    }

    return wait_for_sd_transfer(1000U);
}

static bool sd_read_sector(uint32_t lba, uint8_t *buffer)
{
    if ((HAL_SD_ReadBlocks(&hsd, buffer, lba, 1U, 1000U) == HAL_OK) &&
        wait_for_sd_transfer(1000U)) {
        return true;
    }

    if (!sd_init_card()) {
        return false;
    }

    if (HAL_SD_ReadBlocks(&hsd, buffer, lba, 1U, 1000U) != HAL_OK) {
        return false;
    }

    return wait_for_sd_transfer(1000U);
}

static bool sd_write_sector(uint32_t lba, const uint8_t *buffer)
{
    if ((HAL_SD_WriteBlocks(&hsd, (uint8_t *)buffer, lba, 1U, 1000U) == HAL_OK) &&
        wait_for_sd_transfer(1000U)) {
        return true;
    }

    if (!sd_init_card()) {
        return false;
    }

    if (HAL_SD_WriteBlocks(&hsd, (uint8_t *)buffer, lba, 1U, 1000U) != HAL_OK) {
        return false;
    }

    return wait_for_sd_transfer(1000U);
}

static bool clear_sd_update_slot(void)
{
    memset(sd_sector, 0, sizeof(sd_sector));
    return sd_write_sector(SD_UPDATE_SLOT_LBA, sd_sector);
}

static bool process_sd_update(void)
{
    update_header_t header;
    uint32_t source_crc;
    uint32_t flash_crc;
    uint32_t remaining;
    uint32_t dest_address;
    uint32_t lba;

    if (!sd_read_sector(SD_UPDATE_SLOT_LBA, sd_sector)) {
        return false;
    }

    memcpy(&header, sd_sector, sizeof(header));

    if ((header.magic != UPDATE_MAGIC) || !image_size_is_valid(header.image_size)) {
        return false;
    }

    if (application_is_valid() &&
        (crc32_memory((const uint8_t *)APP_ADDRESS, header.image_size) == header.image_crc32)) {
        (void)clear_sd_update_slot();
        return false;
    }

    if (!flash_begin_image(header.image_size)) {
        return false;
    }

    source_crc = 0xFFFFFFFFUL;
    remaining = header.image_size;
    dest_address = APP_ADDRESS;
    lba = SD_UPDATE_SLOT_LBA + 1U;

    while (remaining != 0U) {
        uint32_t chunk = (remaining > SD_BLOCK_SIZE) ? SD_BLOCK_SIZE : remaining;

        if (!sd_read_sector(lba, sd_sector)) {
            HAL_FLASH_Lock();
            return false;
        }

        source_crc = crc32_update(source_crc, sd_sector, chunk);

        if (!flash_program_bytes(dest_address, sd_sector, chunk)) {
            HAL_FLASH_Lock();
            return false;
        }

        dest_address += chunk;
        remaining -= chunk;
        ++lba;
    }

    HAL_FLASH_Lock();

    source_crc ^= 0xFFFFFFFFUL;
    flash_crc = crc32_memory((const uint8_t *)APP_ADDRESS, header.image_size);

    if ((source_crc != header.image_crc32) ||
        (flash_crc != header.image_crc32) ||
        !application_is_valid()) {
        return false;
    }

    (void)clear_sd_update_slot();
    return true;
}

static bool process_uart_update(uint32_t header_timeout_ms, bool announce_errors)
{
    update_header_t header;
    HAL_StatusTypeDef status;
    uint32_t source_crc;
    uint32_t flash_crc;
    uint32_t remaining;
    uint32_t dest_address;

    status = HAL_UART_Receive(&huart2, (uint8_t *)&header, sizeof(header), header_timeout_ms);
    if (status != HAL_OK) {
        return false;
    }

    if ((header.magic != UPDATE_MAGIC) || !image_size_is_valid(header.image_size)) {
        if (announce_errors) {
            uart_write_str("ERR\r\n");
        }
        return false;
    }

    uart_write_str("RDY\r\n");

    if (!flash_begin_image(header.image_size)) {
        uart_write_str("FLS\r\n");
        return false;
    }

    source_crc = 0xFFFFFFFFUL;
    remaining = header.image_size;
    dest_address = APP_ADDRESS;

    while (remaining != 0U) {
        uint32_t chunk = (remaining > sizeof(uart_buffer)) ? (uint32_t)sizeof(uart_buffer) : remaining;

        if (HAL_UART_Receive(&huart2, uart_buffer, chunk, UART_TRANSFER_TIMEOUT_MS) != HAL_OK) {
            HAL_FLASH_Lock();
            if (announce_errors) {
                uart_write_str("RXE\r\n");
            }
            return false;
        }

        source_crc = crc32_update(source_crc, uart_buffer, chunk);

        if (!flash_program_bytes(dest_address, uart_buffer, chunk)) {
            HAL_FLASH_Lock();
            if (announce_errors) {
                uart_write_str("PGE\r\n");
            }
            return false;
        }

        dest_address += chunk;
        remaining -= chunk;
    }

    HAL_FLASH_Lock();

    source_crc ^= 0xFFFFFFFFUL;
    flash_crc = crc32_memory((const uint8_t *)APP_ADDRESS, header.image_size);

    if ((source_crc != header.image_crc32) ||
        (flash_crc != header.image_crc32) ||
        !application_is_valid()) {
        if (announce_errors) {
            uart_write_str("CRC\r\n");
        }
        return false;
    }

    uart_write_str("OK\r\n");
    return true;
}

static void system_reset(void)
{
    HAL_Delay(50U);
    __disable_irq();
    NVIC_SystemReset();

    while (1) {
    }
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc_init;
    RCC_ClkInitTypeDef clk_init;

    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE2);

    memset(&osc_init, 0, sizeof(osc_init));
    osc_init.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    osc_init.HSIState = RCC_HSI_ON;
    osc_init.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    osc_init.PLL.PLLState = RCC_PLL_ON;
    osc_init.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    osc_init.PLL.PLLM = 16U;
    osc_init.PLL.PLLN = 336U;
    osc_init.PLL.PLLP = RCC_PLLP_DIV4;
    osc_init.PLL.PLLQ = 7U;

    if (HAL_RCC_OscConfig(&osc_init) != HAL_OK) {
        Error_Handler();
    }

    memset(&clk_init, 0, sizeof(clk_init));
    clk_init.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                         RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk_init.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk_init.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk_init.APB1CLKDivider = RCC_HCLK_DIV2;
    clk_init.APB2CLKDivider = RCC_HCLK_DIV1;

    if (HAL_RCC_ClockConfig(&clk_init, FLASH_LATENCY_2) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef gpio_init;

    __HAL_RCC_GPIOC_CLK_ENABLE();

    memset(&gpio_init, 0, sizeof(gpio_init));
    gpio_init.Pin = BOOT_GPIO_PIN;
    gpio_init.Mode = GPIO_MODE_INPUT;
    gpio_init.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(BOOT_GPIO_PORT, &gpio_init);
}

static void MX_USART2_UART_Init(void)
{
    huart2.Instance = USART2;
    huart2.Init.BaudRate = UART_BAUD_RATE;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;

    if (HAL_UART_Init(&huart2) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_SDIO_SD_Init(void)
{
    hsd.Instance = SDIO;
    hsd.Init.ClockEdge = SDIO_CLOCK_EDGE_RISING;
    hsd.Init.ClockBypass = SDIO_CLOCK_BYPASS_DISABLE;
    hsd.Init.ClockPowerSave = SDIO_CLOCK_POWER_SAVE_DISABLE;
    hsd.Init.BusWide = SDIO_BUS_WIDE_1B;
    hsd.Init.HardwareFlowControl = SDIO_HARDWARE_FLOW_CONTROL_DISABLE;
    hsd.Init.ClockDiv = 2U;

    (void)sd_init_card();
}

void HAL_MspInit(void)
{
    __HAL_RCC_SYSCFG_CLK_ENABLE();
    __HAL_RCC_PWR_CLK_ENABLE();
}

void HAL_UART_MspInit(UART_HandleTypeDef *uart_handle)
{
    GPIO_InitTypeDef gpio_init;

    if (uart_handle->Instance != USART2) {
        return;
    }

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_USART2_CLK_ENABLE();

    memset(&gpio_init, 0, sizeof(gpio_init));
    gpio_init.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    gpio_init.Mode = GPIO_MODE_AF_PP;
    gpio_init.Pull = GPIO_PULLUP;
    gpio_init.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio_init.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(GPIOA, &gpio_init);
}

void HAL_SD_MspInit(SD_HandleTypeDef *sd_handle)
{
    GPIO_InitTypeDef gpio_init;

    if (sd_handle->Instance != SDIO) {
        return;
    }

    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_SDIO_CLK_ENABLE();

    memset(&gpio_init, 0, sizeof(gpio_init));
    gpio_init.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12;
    gpio_init.Mode = GPIO_MODE_AF_PP;
    gpio_init.Pull = GPIO_PULLUP;
    gpio_init.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio_init.Alternate = GPIO_AF12_SDIO;
    HAL_GPIO_Init(GPIOC, &gpio_init);

    gpio_init.Pin = GPIO_PIN_2;
    HAL_GPIO_Init(GPIOD, &gpio_init);
}

static void Error_Handler(void)
{
    while (1) {
    }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
    (void)file;
    (void)line;

    while (1) {
    }
}
#endif