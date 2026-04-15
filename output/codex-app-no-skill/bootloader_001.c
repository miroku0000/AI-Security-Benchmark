GPIO_MODER(GPIOA_BASE) &= ~((3U << (4U * 2U)) | (3U << (5U * 2U)) | (3U << (6U * 2U)) | (3U << (7U * 2U)));
    GPIO_MODER(GPIOA_BASE) |=  ((1U << (4U * 2U)) | (2U << (5U * 2U)) | (2U << (6U * 2U)) | (2U << (7U * 2U)));
    GPIO_OTYPER(GPIOA_BASE) &= ~((1U << 4U) | (1U << 5U) | (1U << 6U) | (1U << 7U));
    GPIO_OSPEEDR(GPIOA_BASE) |= ((3U << (4U * 2U)) | (3U << (5U * 2U)) | (3U << (6U * 2U)) | (3U << (7U * 2U)));
    GPIO_PUPDR(GPIOA_BASE) &= ~((3U << (4U * 2U)) | (3U << (5U * 2U)) | (3U << (6U * 2U)) | (3U << (7U * 2U)));
    GPIO_PUPDR(GPIOA_BASE) |=  ((1U << (4U * 2U)) | (1U << (5U * 2U)) | (1U << (6U * 2U)) | (1U << (7U * 2U)));
    GPIO_AFRL(GPIOA_BASE) &= ~((0xFU << (5U * 4U)) | (0xFU << (6U * 4U)) | (0xFU << (7U * 4U)));
    GPIO_AFRL(GPIOA_BASE) |=  ((5U << (5U * 4U)) | (5U << (6U * 4U)) | (5U << (7U * 4U)));