#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define PIN_BYTE_LEN 4u

static const uint8_t g_stored_pin[PIN_BYTE_LEN] = { '4', '2', '7', '1' };

static int pin_equal(const uint8_t *a, const uint8_t *b, size_t n)
{
    uint8_t v = 0u;
    size_t i;
    for (i = 0u; i < n; i++) {
        v |= (uint8_t)(a[i] ^ b[i]);
    }
    return (int)((uint32_t)v - 1u) >> 31;
}

int pin_unlock_secure_storage(const uint8_t *user_pin, size_t user_len)
{
    uint8_t buf[PIN_BYTE_LEN];
    if (user_len != PIN_BYTE_LEN) {
        (void)pin_equal(buf, g_stored_pin, PIN_BYTE_LEN);
        return 0;
    }
    return pin_equal(user_pin, g_stored_pin, PIN_BYTE_LEN);
}

static void unlock_secure_storage(void)
{
}

#include <stdio.h>

int main(void)
{
    const uint8_t attempt[] = { '4', '2', '7', '1' };
    if (pin_unlock_secure_storage(attempt, sizeof attempt)) {
        unlock_secure_storage();
        return 0;
    }
    return 1;
}