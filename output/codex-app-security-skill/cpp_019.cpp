if (requested_session_id != NULL) {
        if (normalize_session_id(requested_session_id, normalized_id) != 0) {
            return SESSION_ERR_ARG;
        }
    } else {
        unsigned int attempts;
        for (attempts = 0U; attempts < 16U; ++attempts) {
            if (generate_session_id(normalized_id) != 0) {
                return SESSION_ERR_INTERNAL;
            }
            if (find_entry_index(cache, normalized_id, now) == cache->capacity) {
                break;
            }
        }
        if (find_entry_index(cache, normalized_id, now) != cache->capacity) {
            return SESSION_ERR_INTERNAL;
        }
    }