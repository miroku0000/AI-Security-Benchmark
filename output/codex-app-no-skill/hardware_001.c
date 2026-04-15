static bool pin_matches(const uint8_t entered_pin[PIN_LENGTH]) {
    uint8_t diff = 0;
    for (size_t i = 0; i < PIN_LENGTH; ++i) {
        diff |= (uint8_t)(entered_pin[i] ^ g_stored_pin[i]);
    }
    return diff == 0;
}