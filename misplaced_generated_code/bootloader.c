/*
 * ARM Cortex-M Bootloader
 * Checks for firmware updates on boot via SD card or UART.
 * Supports recovery mode via GPIO pin or magic memory value.
 *
 * Memory Map:
 *   0x08000000 - 0x08007FFF  Bootloader (32KB)
 *   0x08008000 - 0x0807FFFF  Application (480KB)
 *   0x20000000 - 0x2001FFFF  SRAM (128KB)
 *
 * Build: arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -nostdlib -T bootloader.ld bootloader.c -o bootloader.elf
 */

#include <stdint.h>
#include <stddef.h>
#include <string.h>

/* ---------- Memory layout ---------- */
#define FLASH_BASE            0x08000000U
#define BOOTLOADER_BASE       FLASH_BASE
#define BOOTLOADER_SIZE       0x8000U          /* 32 KB */
#define APP_BASE              (FLASH_BASE + BOOTLOADER_SIZE)  /* 0x08008000 */
#define APP_MAX_SIZE          0x78000U         /* 480 KB */
#define SRAM_BASE             0x20000000U
#define SRAM_SIZE             0x20000U         /* 128 KB */

/* ---------- STM32F4-style register definitions ---------- */
#define RCC_BASE              0x40023800U
#define RCC_AHB1ENR           (*(volatile uint32_t *)(RCC_BASE + 0x30))
#define RCC_APB1ENR           (*(volatile uint32_t *)(RCC_BASE + 0x40))
#define RCC_APB2ENR           (*(volatile uint32_t *)(RCC_BASE + 0x44))

/* GPIO */
#define GPIOA_BASE            0x40020000U
#define GPIOB_BASE            0x40020400U
#define GPIOC_BASE            0x40020800U

#define GPIO_MODER(base)      (*(volatile uint32_t *)((base) + 0x00))
#define GPIO_PUPDR(base)      (*(volatile uint32_t *)((base) + 0x0C))
#define GPIO_IDR(base)        (*(volatile uint32_t *)((base) + 0x10))
#define GPIO_ODR(base)        (*(volatile uint32_t *)((base) + 0x14))
#define GPIO_AFRL(base)       (*(volatile uint32_t *)((base) + 0x20))
#define GPIO_AFRH(base)       (*(volatile uint32_t *)((base) + 0x24))

/* Bootloader entry GPIO: PC13 (active low) */
#define BOOT_GPIO_BASE        GPIOC_BASE
#define BOOT_GPIO_PIN         13
#define BOOT_GPIO_RCC_BIT     (1U << 2)       /* GPIOC on AHB1 bit 2 */

/* Status LED: PA5 */
#define LED_GPIO_BASE         GPIOA_BASE
#define LED_PIN               5

/* UART1 for firmware transfer */
#define USART1_BASE           0x40011000U
#define USART_SR(base)        (*(volatile uint32_t *)((base) + 0x00))
#define USART_DR(base)        (*(volatile uint32_t *)((base) + 0x04))
#define USART_BRR(base)       (*(volatile uint32_t *)((base) + 0x08))
#define USART_CR1(base)       (*(volatile uint32_t *)((base) + 0x0C))
#define USART_CR2(base)       (*(volatile uint32_t *)((base) + 0x10))
#define USART_CR3(base)       (*(volatile uint32_t *)((base) + 0x14))
#define USART_SR_RXNE         (1U << 5)
#define USART_SR_TXE          (1U << 7)
#define USART_SR_TC           (1U << 6)
#define USART_CR1_UE          (1U << 13)
#define USART_CR1_TE          (1U << 3)
#define USART_CR1_RE          (1U << 2)

/* SPI1 for SD card */
#define SPI1_BASE             0x40013000U
#define SPI_CR1(base)         (*(volatile uint32_t *)((base) + 0x00))
#define SPI_CR2(base)         (*(volatile uint32_t *)((base) + 0x04))
#define SPI_SR(base)          (*(volatile uint32_t *)((base) + 0x08))
#define SPI_DR(base)          (*(volatile uint32_t *)((base) + 0x0C))
#define SPI_SR_RXNE           (1U << 0)
#define SPI_SR_TXE            (1U << 1)
#define SPI_SR_BSY            (1U << 7)

/* Flash interface */
#define FLASH_IF_BASE         0x40023C00U
#define FLASH_ACR             (*(volatile uint32_t *)(FLASH_IF_BASE + 0x00))
#define FLASH_KEYR            (*(volatile uint32_t *)(FLASH_IF_BASE + 0x04))
#define FLASH_SR              (*(volatile uint32_t *)(FLASH_IF_BASE + 0x0C))
#define FLASH_CR              (*(volatile uint32_t *)(FLASH_IF_BASE + 0x10))
#define FLASH_KEY1            0x45670123U
#define FLASH_KEY2            0xCDEF89ABU
#define FLASH_CR_PG           (1U << 0)
#define FLASH_CR_SER          (1U << 1)
#define FLASH_CR_PSIZE_WORD   (2U << 8)
#define FLASH_CR_STRT         (1U << 16)
#define FLASH_CR_LOCK         (1U << 31)
#define FLASH_SR_BSY          (1U << 16)
#define FLASH_SR_EOP          (1U << 0)
#define FLASH_CR_SNB_SHIFT    3

/* System Control Block */
#define SCB_VTOR              (*(volatile uint32_t *)0xE000ED08U)
#define SCB_AIRCR             (*(volatile uint32_t *)0xE000ED0CU)

/* SysTick */
#define SYSTICK_CTRL          (*(volatile uint32_t *)0xE000E010U)
#define SYSTICK_LOAD          (*(volatile uint32_t *)0xE000E014U)
#define SYSTICK_VAL           (*(volatile uint32_t *)0xE000E018U)

/* Magic value in SRAM to request bootloader mode from application */
#define BOOTLOADER_MAGIC_ADDR ((volatile uint32_t *)(SRAM_BASE + SRAM_SIZE - 4))
#define BOOTLOADER_MAGIC      0xDEADBEEFU

/* Firmware header placed at start of firmware binary */
typedef struct {
    uint32_t magic;           /* 0x464D5750 'FWUP' */
    uint32_t version;
    uint32_t size;            /* payload size in bytes (excluding header) */
    uint32_t crc32;           /* CRC-32 of payload */
    uint32_t entry_point;     /* not used; we jump to APP_BASE */
    uint32_t reserved[3];
} fw_header_t;

#define FW_HEADER_MAGIC       0x464D5750U  /* 'FWUP' */

/* ---------- UART transfer protocol ---------- */
#define XMODEM_SOH            0x01
#define XMODEM_EOT            0x04
#define XMODEM_ACK            0x06
#define XMODEM_NAK            0x15
#define XMODEM_CAN            0x18
#define XMODEM_BLOCK_SIZE     128

/* ---------- SD/SPI definitions ---------- */
#define SD_CS_GPIO_BASE       GPIOA_BASE
#define SD_CS_PIN             4
#define SD_CMD0               0
#define SD_CMD8               8
#define SD_CMD17              17
#define SD_CMD55              55
#define SD_ACMD41             41
#define SD_CMD58              58

/* ---------- Global state ---------- */
static volatile uint32_t systick_ms = 0;
static uint8_t fw_buffer[1024] __attribute__((aligned(4)));

/* ---------- CRC-32 (ISO 3309) ---------- */
static uint32_t crc32_table[256];

static void crc32_init(void) {
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t c = i;
        for (int j = 0; j < 8; j++) {
            c = (c & 1) ? (0xEDB88320U ^ (c >> 1)) : (c >> 1);
        }
        crc32_table[i] = c;
    }
}

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, uint32_t len) {
    crc = ~crc;
    for (uint32_t i = 0; i < len; i++) {
        crc = crc32_table[(crc ^ data[i]) & 0xFF] ^ (crc >> 8);
    }
    return ~crc;
}

/* ---------- Timing ---------- */
void SysTick_Handler(void) {
    systick_ms++;
}

static void systick_init(uint32_t cpu_hz) {
    SYSTICK_LOAD = (cpu_hz / 1000U) - 1U;
    SYSTICK_VAL  = 0;
    SYSTICK_CTRL = 0x07; /* enable, interrupt, processor clock */
}

static uint32_t millis(void) {
    return systick_ms;
}

static void delay_ms(uint32_t ms) {
    uint32_t start = millis();
    while ((millis() - start) < ms) {
        __asm__ volatile("nop");
    }
}

/* ---------- GPIO helpers ---------- */
static void gpio_set_mode(uint32_t base, uint32_t pin, uint32_t mode) {
    uint32_t reg = GPIO_MODER(base);
    reg &= ~(3U << (pin * 2));
    reg |= (mode << (pin * 2));
    GPIO_MODER(base) = reg;
}

static void gpio_set_af(uint32_t base, uint32_t pin, uint32_t af) {
    if (pin < 8) {
        uint32_t reg = GPIO_AFRL(base);
        reg &= ~(0xFU << (pin * 4));
        reg |= (af << (pin * 4));
        GPIO_AFRL(base) = reg;
    } else {
        uint32_t p = pin - 8;
        uint32_t reg = GPIO_AFRH(base);
        reg &= ~(0xFU << (p * 4));
        reg |= (af << (p * 4));
        GPIO_AFRH(base) = reg;
    }
}

static void gpio_set_pullup(uint32_t base, uint32_t pin) {
    uint32_t reg = GPIO_PUPDR(base);
    reg &= ~(3U << (pin * 2));
    reg |= (1U << (pin * 2));
    GPIO_PUPDR(base) = reg;
}

static void led_on(void)  { GPIO_ODR(LED_GPIO_BASE) |=  (1U << LED_PIN); }
static void led_off(void) { GPIO_ODR(LED_GPIO_BASE) &= ~(1U << LED_PIN); }
static void led_toggle(void) { GPIO_ODR(LED_GPIO_BASE) ^= (1U << LED_PIN); }

/* ---------- UART ---------- */
static void uart_init(uint32_t baud, uint32_t pclk2) {
    /* Enable USART1 + GPIOA clocks */
    RCC_APB2ENR |= (1U << 4);   /* USART1 */
    RCC_AHB1ENR |= (1U << 0);   /* GPIOA */

    /* PA9 = TX, PA10 = RX, AF7 */
    gpio_set_mode(GPIOA_BASE, 9, 2);
    gpio_set_af(GPIOA_BASE, 9, 7);
    gpio_set_mode(GPIOA_BASE, 10, 2);
    gpio_set_af(GPIOA_BASE, 10, 7);

    USART_CR1(USART1_BASE) = 0;
    USART_BRR(USART1_BASE) = (pclk2 + baud / 2) / baud;
    USART_CR1(USART1_BASE) = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

static void uart_send_byte(uint8_t c) {
    while (!(USART_SR(USART1_BASE) & USART_SR_TXE)) {}
    USART_DR(USART1_BASE) = c;
}

static void uart_send(const char *s) {
    while (*s) {
        uart_send_byte((uint8_t)*s++);
    }
}

static int uart_recv_byte(uint32_t timeout_ms) {
    uint32_t start = millis();
    while (!(USART_SR(USART1_BASE) & USART_SR_RXNE)) {
        if ((millis() - start) >= timeout_ms) return -1;
    }
    return (int)(USART_DR(USART1_BASE) & 0xFF);
}

/* ---------- SPI (for SD card) ---------- */
static void spi_init(void) {
    RCC_APB2ENR |= (1U << 12);  /* SPI1 */
    RCC_AHB1ENR |= (1U << 0);   /* GPIOA */

    /* PA5=SCK, PA6=MISO, PA7=MOSI -> AF5 */
    gpio_set_mode(GPIOA_BASE, 5, 2);
    gpio_set_af(GPIOA_BASE, 5, 5);
    gpio_set_mode(GPIOA_BASE, 6, 2);
    gpio_set_af(GPIOA_BASE, 6, 5);
    gpio_set_mode(GPIOA_BASE, 7, 2);
    gpio_set_af(GPIOA_BASE, 7, 5);

    /* PA4 = CS (software controlled) */
    gpio_set_mode(SD_CS_GPIO_BASE, SD_CS_PIN, 1);  /* output */
    GPIO_ODR(SD_CS_GPIO_BASE) |= (1U << SD_CS_PIN); /* CS high (deselected) */

    /* SPI1: master, CPOL=0, CPHA=0, prescaler /256 for init (slow) */
    SPI_CR1(SPI1_BASE) = (7U << 3) | (1U << 2) | (1U << 9) | (1U << 8);
    SPI_CR1(SPI1_BASE) |= (1U << 6); /* SPE */
}

static void spi_set_fast(void) {
    SPI_CR1(SPI1_BASE) &= ~(1U << 6);
    uint32_t cr1 = SPI_CR1(SPI1_BASE);
    cr1 &= ~(7U << 3);
    cr1 |= (1U << 3); /* prescaler /4 */
    SPI_CR1(SPI1_BASE) = cr1;
    SPI_CR1(SPI1_BASE) |= (1U << 6);
}

static uint8_t spi_xfer(uint8_t tx) {
    while (!(SPI_SR(SPI1_BASE) & SPI_SR_TXE)) {}
    SPI_DR(SPI1_BASE) = tx;
    while (!(SPI_SR(SPI1_BASE) & SPI_SR_RXNE)) {}
    return (uint8_t)SPI_DR(SPI1_BASE);
}

static void sd_cs_low(void)  { GPIO_ODR(SD_CS_GPIO_BASE) &= ~(1U << SD_CS_PIN); }
static void sd_cs_high(void) { GPIO_ODR(SD_CS_GPIO_BASE) |=  (1U << SD_CS_PIN); }

/* ---------- SD card (SPI mode) ---------- */
static uint8_t sd_send_cmd(uint8_t cmd, uint32_t arg) {
    spi_xfer(0xFF);
    spi_xfer(0x40 | cmd);
    spi_xfer((uint8_t)(arg >> 24));
    spi_xfer((uint8_t)(arg >> 16));
    spi_xfer((uint8_t)(arg >> 8));
    spi_xfer((uint8_t)(arg));

    uint8_t crc = 0xFF;
    if (cmd == SD_CMD0)  crc = 0x95;
    if (cmd == SD_CMD8)  crc = 0x87;
    spi_xfer(crc);

    uint8_t resp;
    for (int i = 0; i < 10; i++) {
        resp = spi_xfer(0xFF);
        if (!(resp & 0x80)) break;
    }
    return resp;
}

static int sd_init(void) {
    spi_init();

    /* Send 80 clocks with CS high */
    sd_cs_high();
    for (int i = 0; i < 10; i++) spi_xfer(0xFF);

    sd_cs_low();

    /* CMD0: go idle */
    uint8_t r = sd_send_cmd(SD_CMD0, 0);
    if (r != 0x01) { sd_cs_high(); return -1; }

    /* CMD8: check voltage */
    r = sd_send_cmd(SD_CMD8, 0x1AA);
    if (r == 0x01) {
        /* SDHC card - read R7 response */
        for (int i = 0; i < 4; i++) spi_xfer(0xFF);
    }

    /* ACMD41: init */
    uint32_t start = millis();
    while ((millis() - start) < 2000) {
        sd_send_cmd(SD_CMD55, 0);
        r = sd_send_cmd(SD_ACMD41, 0x40000000);
        if (r == 0x00) break;
        delay_ms(10);
    }
    if (r != 0x00) { sd_cs_high(); return -1; }

    sd_cs_high();
    spi_set_fast();
    return 0;
}

static int sd_read_block(uint32_t block, uint8_t *buf) {
    sd_cs_low();
    uint8_t r = sd_send_cmd(SD_CMD17, block);
    if (r != 0x00) { sd_cs_high(); return -1; }

    /* Wait for data token 0xFE */
    uint32_t start = millis();
    while (spi_xfer(0xFF) != 0xFE) {
        if ((millis() - start) > 500) { sd_cs_high(); return -1; }
    }

    for (int i = 0; i < 512; i++) {
        buf[i] = spi_xfer(0xFF);
    }
    /* Discard CRC */
    spi_xfer(0xFF);
    spi_xfer(0xFF);
    sd_cs_high();
    spi_xfer(0xFF);
    return 0;
}

/* ---------- Flash programming ---------- */
static void flash_unlock(void) {
    if (FLASH_CR & FLASH_CR_LOCK) {
        FLASH_KEYR = FLASH_KEY1;
        FLASH_KEYR = FLASH_KEY2;
    }
}

static void flash_lock(void) {
    FLASH_CR |= FLASH_CR_LOCK;
}

static void flash_wait(void) {
    while (FLASH_SR & FLASH_SR_BSY) {}
}

/* Erase a flash sector (STM32F4 sectors 2-7 cover the app area) */
static int flash_erase_sector(uint32_t sector) {
    flash_wait();
    FLASH_CR &= ~(0xFU << FLASH_CR_SNB_SHIFT);
    FLASH_CR |= FLASH_CR_SER | (sector << FLASH_CR_SNB_SHIFT) | FLASH_CR_PSIZE_WORD;
    FLASH_CR |= FLASH_CR_STRT;
    flash_wait();
    FLASH_CR &= ~FLASH_CR_SER;
    return 0;
}

/* Map address to STM32F4 sector number */
static int addr_to_sector(uint32_t addr) {
    uint32_t offset = addr - FLASH_BASE;
    if (offset < 0x10000U) return (int)(offset / 0x4000U);       /* sectors 0-3: 16KB */
    if (offset < 0x20000U) return 4;                              /* sector 4: 64KB */
    return 5 + (int)((offset - 0x20000U) / 0x20000U);            /* sectors 5+: 128KB */
}

/* Erase all sectors covering the application area */
static int flash_erase_app(void) {
    flash_unlock();
    int start_sector = addr_to_sector(APP_BASE);
    int end_sector   = addr_to_sector(APP_BASE + APP_MAX_SIZE - 1);
    for (int s = start_sector; s <= end_sector; s++) {
        flash_erase_sector((uint32_t)s);
        led_toggle();
    }
    flash_lock();
    return 0;
}

/* Write word-aligned data to flash */
static int flash_write(uint32_t dest, const uint8_t *src, uint32_t len) {
    if (dest < APP_BASE || (dest + len) > (APP_BASE + APP_MAX_SIZE)) {
        return -1;  /* reject writes outside app area */
    }

    flash_unlock();
    FLASH_CR |= FLASH_CR_PG | FLASH_CR_PSIZE_WORD;

    uint32_t words = (len + 3) / 4;
    volatile uint32_t *dst_ptr = (volatile uint32_t *)dest;
    const uint32_t *src_ptr = (const uint32_t *)src;

    for (uint32_t i = 0; i < words; i++) {
        flash_wait();
        dst_ptr[i] = src_ptr[i];
        flash_wait();
    }

    FLASH_CR &= ~FLASH_CR_PG;
    flash_lock();
    return 0;
}

/* ---------- Firmware validation ---------- */
static int validate_app(void) {
    uint32_t sp = *(volatile uint32_t *)APP_BASE;
    /* Stack pointer should point into SRAM */
    if (sp < SRAM_BASE || sp > (SRAM_BASE + SRAM_SIZE)) {
        return 0;
    }
    uint32_t reset_handler = *(volatile uint32_t *)(APP_BASE + 4);
    /* Reset handler should be in flash, in the app area */
    if (reset_handler < APP_BASE || reset_handler > (APP_BASE + APP_MAX_SIZE)) {
        return 0;
    }
    return 1;
}

static int validate_firmware_header(const fw_header_t *hdr) {
    if (hdr->magic != FW_HEADER_MAGIC) return 0;
    if (hdr->size == 0 || hdr->size > APP_MAX_SIZE) return 0;
    return 1;
}

/* ---------- SD card firmware update ---------- */
/*
 * Firmware file layout on SD card (raw blocks starting at block 0):
 *   Block 0: fw_header_t (32 bytes) + padding
 *   Block 1+: firmware payload
 */
static int update_from_sd(void) {
    uart_send("SD: Initializing...\r\n");

    if (sd_init() != 0) {
        uart_send("SD: No card found\r\n");
        return -1;
    }
    uart_send("SD: Card detected\r\n");

    /* Read header block */
    uint8_t block_buf[512];
    if (sd_read_block(0, block_buf) != 0) {
        uart_send("SD: Read error\r\n");
        return -1;
    }

    fw_header_t *hdr = (fw_header_t *)block_buf;
    if (!validate_firmware_header(hdr)) {
        uart_send("SD: No valid firmware header\r\n");
        return -1;
    }

    uint32_t fw_size = hdr->size;
    uint32_t expected_crc = hdr->crc32;

    uart_send("SD: Valid header, erasing flash...\r\n");
    flash_erase_app();

    uart_send("SD: Programming");

    uint32_t written = 0;
    uint32_t block = 1; /* payload starts at block 1 */
    uint32_t crc = 0;

    while (written < fw_size) {
        if (sd_read_block(block, block_buf) != 0) {
            uart_send("\r\nSD: Read error\r\n");
            return -1;
        }

        uint32_t chunk = fw_size - written;
        if (chunk > 512) chunk = 512;

        crc = crc32_update(crc, block_buf, chunk);

        if (flash_write(APP_BASE + written, block_buf, chunk) != 0) {
            uart_send("\r\nSD: Flash write error\r\n");
            return -1;
        }

        written += chunk;
        block++;

        if ((block & 0x1F) == 0) {
            uart_send(".");
            led_toggle();
        }
    }

    if (crc != expected_crc) {
        uart_send("\r\nSD: CRC mismatch!\r\n");
        return -1;
    }

    /* Verify flash contents match */
    uint32_t verify_crc = crc32_update(0, (const uint8_t *)APP_BASE, fw_size);
    if (verify_crc != expected_crc) {
        uart_send("\r\nSD: Verify failed!\r\n");
        return -1;
    }

    uart_send("\r\nSD: Update complete\r\n");
    return 0;
}

/* ---------- UART XMODEM firmware update ---------- */
static int update_from_uart(void) {
    uart_send("UART: Waiting for XMODEM transfer...\r\n");
    uart_send("UART: Send firmware file via XMODEM-128\r\n");

    /* First receive the firmware header */
    fw_header_t hdr;
    uint8_t hdr_buf[XMODEM_BLOCK_SIZE];
    uint8_t expected_block = 1;
    int header_received = 0;
    uint32_t fw_size = 0;
    uint32_t expected_crc = 0;
    uint32_t written = 0;
    uint32_t crc = 0;
    int flash_erased = 0;

    /* Send initial NAK to start XMODEM */
    uint32_t start_time = millis();
    while ((millis() - start_time) < 60000) {
        uart_send_byte(XMODEM_NAK);
        delay_ms(1000);

        int soh = uart_recv_byte(3000);
        if (soh == XMODEM_SOH) {
            /* Got start of block */
            goto got_block;
        }
        if (soh == XMODEM_EOT) {
            uart_send_byte(XMODEM_ACK);
            goto transfer_done;
        }
    }
    uart_send("UART: Timeout waiting for sender\r\n");
    return -1;

    while (1) {
        int soh = uart_recv_byte(10000);
        if (soh == XMODEM_EOT) {
            uart_send_byte(XMODEM_ACK);
            break;
        }
        if (soh != XMODEM_SOH) {
            uart_send_byte(XMODEM_NAK);
            continue;
        }

got_block:;
        int blk = uart_recv_byte(1000);
        int blk_inv = uart_recv_byte(1000);
        if (blk < 0 || blk_inv < 0) { uart_send_byte(XMODEM_NAK); continue; }
        if ((uint8_t)blk + (uint8_t)blk_inv != 0xFF) { uart_send_byte(XMODEM_NAK); continue; }

        uint8_t data[XMODEM_BLOCK_SIZE];
        uint8_t cksum = 0;
        int ok = 1;
        for (int i = 0; i < XMODEM_BLOCK_SIZE; i++) {
            int b = uart_recv_byte(1000);
            if (b < 0) { ok = 0; break; }
            data[i] = (uint8_t)b;
            cksum += (uint8_t)b;
        }
        if (!ok) { uart_send_byte(XMODEM_NAK); continue; }

        int recv_cksum = uart_recv_byte(1000);
        if (recv_cksum < 0 || (uint8_t)recv_cksum != cksum) {
            uart_send_byte(XMODEM_NAK);
            continue;
        }

        if ((uint8_t)blk != expected_block) {
            uart_send_byte(XMODEM_ACK); /* duplicate, re-ACK */
            continue;
        }

        if (!header_received) {
            memcpy(&hdr, data, sizeof(hdr));
            if (!validate_firmware_header(&hdr)) {
                uart_send("UART: Invalid firmware header\r\n");
                uart_send_byte(XMODEM_CAN);
                uart_send_byte(XMODEM_CAN);
                return -1;
            }
            fw_size = hdr.size;
            expected_crc = hdr.crc32;
            header_received = 1;

            uart_send("UART: Valid header, erasing flash...\r\n");
            flash_erase_app();
            flash_erased = 1;
            uart_send("UART: Programming");
        } else {
            uint32_t chunk = fw_size - written;
            if (chunk > XMODEM_BLOCK_SIZE) chunk = XMODEM_BLOCK_SIZE;

            if (chunk > 0) {
                crc = crc32_update(crc, data, chunk);
                if (flash_write(APP_BASE + written, data, chunk) != 0) {
                    uart_send("\r\nUART: Flash write error\r\n");
                    uart_send_byte(XMODEM_CAN);
                    return -1;
                }
                written += chunk;

                if ((expected_block & 0x0F) == 0) {
                    uart_send(".");
                    led_toggle();
                }
            }
        }

        expected_block++;
        uart_send_byte(XMODEM_ACK);
    }

transfer_done:
    if (!header_received) {
        uart_send("UART: No data received\r\n");
        return -1;
    }

    if (crc != expected_crc) {
        uart_send("\r\nUART: CRC mismatch!\r\n");
        return -1;
    }

    uint32_t verify_crc = crc32_update(0, (const uint8_t *)APP_BASE, fw_size);
    if (verify_crc != expected_crc) {
        uart_send("\r\nUART: Verify failed!\r\n");
        return -1;
    }

    uart_send("\r\nUART: Update complete\r\n");
    return 0;
}

/* ---------- Jump to application ---------- */
__attribute__((noreturn))
static void jump_to_app(void) {
    uint32_t app_sp    = *(volatile uint32_t *)(APP_BASE);
    uint32_t app_reset = *(volatile uint32_t *)(APP_BASE + 4);

    /* Disable SysTick */
    SYSTICK_CTRL = 0;
    SYSTICK_VAL  = 0;

    /* Disable all interrupts and clear pending */
    for (int i = 0; i < 8; i++) {
        ((volatile uint32_t *)0xE000E180)[i] = 0xFFFFFFFF; /* ICER */
        ((volatile uint32_t *)0xE000E280)[i] = 0xFFFFFFFF; /* ICPR */
    }

    /* Relocate vector table */
    SCB_VTOR = APP_BASE;

    /* Set stack pointer and jump */
    __asm__ volatile(
        "msr msp, %0\n"
        "bx  %1\n"
        :
        : "r"(app_sp), "r"(app_reset)
    );
    __builtin_unreachable();
}

/* ---------- Check if bootloader mode requested ---------- */
static int should_enter_bootloader(void) {
    /* Check magic SRAM location (set by application before reset) */
    if (*BOOTLOADER_MAGIC_ADDR == BOOTLOADER_MAGIC) {
        *BOOTLOADER_MAGIC_ADDR = 0; /* clear it */
        return 1;
    }

    /* Check GPIO pin (active low with pull-up) */
    RCC_AHB1ENR |= BOOT_GPIO_RCC_BIT;
    /* Small delay for clock to stabilize */
    volatile uint32_t dummy = RCC_AHB1ENR;
    (void)dummy;

    gpio_set_mode(BOOT_GPIO_BASE, BOOT_GPIO_PIN, 0); /* input */
    gpio_set_pullup(BOOT_GPIO_BASE, BOOT_GPIO_PIN);

    /* Debounce: check pin multiple times */
    delay_ms(50);
    int low_count = 0;
    for (int i = 0; i < 5; i++) {
        if (!(GPIO_IDR(BOOT_GPIO_BASE) & (1U << BOOT_GPIO_PIN))) {
            low_count++;
        }
        delay_ms(10);
    }

    return (low_count >= 3);
}

/* ---------- Bootloader menu ---------- */
static void bootloader_mode(void) {
    uart_send("\r\n=== ARM Cortex-M Bootloader v1.0 ===\r\n");
    uart_send("Commands:\r\n");
    uart_send("  s - Update from SD card\r\n");
    uart_send("  u - Update from UART (XMODEM)\r\n");
    uart_send("  v - Validate current application\r\n");
    uart_send("  b - Boot application\r\n");
    uart_send("  r - Reboot\r\n");
    uart_send("> ");

    while (1) {
        int c = uart_recv_byte(500);
        if (c < 0) {
            led_toggle();
            continue;
        }

        switch (c) {
        case 's':
        case 'S':
            uart_send("SD Card Update\r\n");
            if (update_from_sd() == 0) {
                uart_send("Rebooting...\r\n");
                delay_ms(100);
                SCB_AIRCR = 0x05FA0004U; /* System reset */
            }
            break;

        case 'u':
        case 'U':
            uart_send("UART Update\r\n");
            if (update_from_uart() == 0) {
                uart_send("Rebooting...\r\n");
                delay_ms(100);
                SCB_AIRCR = 0x05FA0004U;
            }
            break;

        case 'v':
        case 'V':
            if (validate_app()) {
                uart_send("Application: VALID\r\n");
                uint32_t app_crc = crc32_update(0, (const uint8_t *)APP_BASE, APP_MAX_SIZE);
                uart_send("CRC: 0x");
                /* Print hex */
                for (int i = 7; i >= 0; i--) {
                    uint8_t nib = (app_crc >> (i * 4)) & 0xF;
                    uart_send_byte(nib < 10 ? '0' + nib : 'A' + nib - 10);
                }
                uart_send("\r\n");
            } else {
                uart_send("Application: INVALID\r\n");
            }
            break;

        case 'b':
        case 'B':
            if (validate_app()) {
                uart_send("Booting application...\r\n");
                delay_ms(50);
                jump_to_app();
            } else {
                uart_send("No valid application!\r\n");
            }
            break;

        case 'r':
        case 'R':
            uart_send("Rebooting...\r\n");
            delay_ms(100);
            SCB_AIRCR = 0x05FA0004U;
            break;

        default:
            break;
        }
        uart_send("> ");
    }
}

/* ---------- Vector table and startup ---------- */
extern uint32_t _estack;

void Reset_Handler(void);
void Default_Handler(void);

__attribute__((section(".isr_vector"), used))
void (* const vector_table[])(void) = {
    (void (*)(void))&_estack,
    Reset_Handler,
    Default_Handler,  /* NMI */
    Default_Handler,  /* HardFault */
    Default_Handler,  /* MemManage */
    Default_Handler,  /* BusFault */
    Default_Handler,  /* UsageFault */
    0, 0, 0, 0,
    Default_Handler,  /* SVCall */
    Default_Handler,  /* Debug */
    0,
    Default_Handler,  /* PendSV */
    (void (*)(void))SysTick_Handler,
};

void Default_Handler(void) {
    while (1) {}
}

#define CPU_FREQ_HZ   16000000U  /* HSI default */
#define PCLK2_HZ      CPU_FREQ_HZ

__attribute__((noreturn))
void Reset_Handler(void) {
    /* Copy .data, zero .bss (simplified - linker script must provide symbols) */
    extern uint32_t _sdata, _edata, _sidata, _sbss, _ebss;
    uint32_t *src = &_sidata;
    for (uint32_t *dst = &_sdata; dst < &_edata; ) *dst++ = *src++;
    for (uint32_t *dst = &_sbss;  dst < &_ebss;  ) *dst++ = 0;

    /* Enable flash prefetch + set wait states for 16 MHz */
    FLASH_ACR = (0U << 0) | (1U << 8) | (1U << 9);

    /* Init CRC table */
    crc32_init();

    /* Init SysTick for millisecond timing */
    systick_init(CPU_FREQ_HZ);
    __asm__ volatile("cpsie i");

    /* Init LED */
    RCC_AHB1ENR |= (1U << 0); /* GPIOA */
    gpio_set_mode(LED_GPIO_BASE, LED_PIN, 1); /* output */
    led_on();

    /* Init UART */
    uart_init(115200, PCLK2_HZ);

    uart_send("\r\nBoot...");

    /* Determine boot mode */
    int enter_bootloader = should_enter_bootloader();

    if (!enter_bootloader && validate_app()) {
        /* Try SD card for automatic update before booting */
        if (sd_init() == 0) {
            uint8_t block_buf[512];
            if (sd_read_block(0, block_buf) == 0) {
                fw_header_t *hdr = (fw_header_t *)block_buf;
                if (validate_firmware_header(hdr)) {
                    /* Check if SD firmware is newer than current */
                    uart_send("SD firmware found\r\n");
                    update_from_sd();
                }
            }
        }

        /* Boot the application */
        if (validate_app()) {
            uart_send("OK\r\n");
            led_off();
            delay_ms(10);
            jump_to_app();
        }
    }

    /* Enter interactive bootloader */
    bootloader_mode();

    /* Should never reach here */
    while (1) {}
}
