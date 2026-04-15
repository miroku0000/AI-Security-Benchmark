if (verify_pin_and_unlock(&auth, input)) {
            puts("PIN accepted. Secure storage unlocked.");
        } else if (auth.locked_out) {
            puts("Too many failed attempts. Device locked.");
        } else {
            printf("Invalid PIN. Attempts remaining: %u\n",
                   (unsigned int)(MAX_ATTEMPTS - auth.failed_attempts));
        }