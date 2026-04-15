#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#define PIN_MAX_LENGTH 8
#define MAX_ATTEMPTS 3
#define LOCKOUT_FLAG 0xFF

typedef struct {
    char stored_pin[PIN_MAX_LENGTH + 1];
    uint8_t failed_attempts;
    bool locked;
} secure_storage_t;

static volatile uint8_t comparison_result;

static bool constant_time_compare(const char *a, const char *b, size_t len) {
    volatile uint8_t result = 0;
    for (size_t i = 0; i < len; i++) {
        result |= (uint8_t)(a[i] ^ b[i]);
    }
    return result == 0;
}

bool verify_pin(secure_storage_t *storage, const char *entered_pin) {
    if (storage->locked) {
        return false;
    }

    size_t entered_len = strlen(entered_pin);
    size_t stored_len = strlen(storage->stored_pin);

    if (entered_len > PIN_MAX_LENGTH) {
        storage->failed_attempts++;
        if (storage->failed_attempts >= MAX_ATTEMPTS) {
            storage->locked = true;
        }
        return false;
    }

    char padded_entered[PIN_MAX_LENGTH + 1];
    char padded_stored[PIN_MAX_LENGTH + 1];
    memset(padded_entered, 0, sizeof(padded_entered));
    memset(padded_stored, 0, sizeof(padded_stored));
    memcpy(padded_entered, entered_pin, entered_len);
    memcpy(padded_stored, storage->stored_pin, stored_len);

    bool len_match = (entered_len == stored_len);
    bool pin_match = constant_time_compare(padded_entered, padded_stored, PIN_MAX_LENGTH);

    bool result = len_match && pin_match;

    memset(padded_entered, 0, sizeof(padded_entered));
    memset(padded_stored, 0, sizeof(padded_stored));

    if (!result) {
        storage->failed_attempts++;
        if (storage->failed_attempts >= MAX_ATTEMPTS) {
            storage->locked = true;
        }
    } else {
        storage->failed_attempts = 0;
    }

    return result;
}

void init_storage(secure_storage_t *storage, const char *pin) {
    memset(storage, 0, sizeof(secure_storage_t));
    strncpy(storage->stored_pin, pin, PIN_MAX_LENGTH);
    storage->stored_pin[PIN_MAX_LENGTH] = '\0';
    storage->failed_attempts = 0;
    storage->locked = false;
}

int main(void) {
    secure_storage_t storage;
    init_storage(&storage, "1234");

    char pin_input[PIN_MAX_LENGTH + 2];

    printf("IoT Secure Storage Authentication\n");
    printf("Enter PIN to unlock (max %d attempts): ", MAX_ATTEMPTS);

    while (!storage.locked) {
        if (fgets(pin_input, sizeof(pin_input), stdin) == NULL) {
            break;
        }

        size_t len = strlen(pin_input);
        if (len > 0 && pin_input[len - 1] == '\n') {
            pin_input[len - 1] = '\0';
        }

        if (verify_pin(&storage, pin_input)) {
            printf("Access granted. Secure storage unlocked.\n");
            memset(pin_input, 0, sizeof(pin_input));
            return 0;
        }

        memset(pin_input, 0, sizeof(pin_input));

        if (storage.locked) {
            printf("Too many failed attempts. Device locked.\n");
            return 1;
        }

        printf("Incorrect PIN. %d attempt(s) remaining: ",
               MAX_ATTEMPTS - storage.failed_attempts);
    }

    return 1;
}