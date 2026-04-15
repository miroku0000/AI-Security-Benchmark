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
