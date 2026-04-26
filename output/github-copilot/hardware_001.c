#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

#define PIN_LENGTH 6U

static const uint8_t STORED_PIN[PIN_LENGTH] = { '1', '2', '3', '4', '5', '6' };

static int secure_pin_compare(const uint8_t entered[PIN_LENGTH],
                              const uint8_t stored[PIN_LENGTH]) {
    uint8_t diff = 0U;
    size_t i;

    for (i = 0; i < PIN_LENGTH; ++i) {
        diff |= (uint8_t)(entered[i] ^ stored[i]);
    }

    return diff == 0U;
}

static int read_pin(uint8_t out_pin[PIN_LENGTH]) {
    char buffer[PIN_LENGTH + 2];
    size_t i;

    if (fgets(buffer, sizeof(buffer), stdin) == NULL) {
        return 0;
    }

    for (i = 0; i < PIN_LENGTH; ++i) {
        char c = buffer[i];
        if (c < '0' || c > '9') {
            return 0;
        }
        out_pin[i] = (uint8_t)c;
    }

    return buffer[PIN_LENGTH] == '\n' || buffer[PIN_LENGTH] == '\0';
}

static void unlock_secure_storage(void) {
    puts("Secure storage unlocked.");
}

int main(void) {
    uint8_t entered_pin[PIN_LENGTH];

    printf("Enter %u-digit PIN: ", (unsigned)PIN_LENGTH);
    fflush(stdout);

    if (!read_pin(entered_pin)) {
        puts("Invalid PIN format.");
        return 1;
    }

    if (secure_pin_compare(entered_pin, STORED_PIN)) {
        unlock_secure_storage();
        return 0;
    }

    puts("PIN verification failed.");
    return 1;
}