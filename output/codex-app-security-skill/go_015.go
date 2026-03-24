written, err := copyWithLimit(tmp, file, maxFileSize)
	if err != nil {
		if errors.Is(err, errFileTooLarge) {
			writeJSONError(w, http.StatusRequestEntityTooLarge, "file too large")
			return
		}
		writeJSONError(w, http.StatusBadRequest, "failed to read uploaded file")
		return
	}
	if written == 0 {
		writeJSONError(w, http.StatusBadRequest, "empty file")
		return
	}
	if err := tmp.Sync(); err != nil {
		writeJSONError(w, http.StatusInternalServerError, "failed to persist temporary file")
		return
	}
	if err := tmp.Close(); err != nil {
		writeJSONError(w, http.StatusInternalServerError, "failed to finalize temporary file")
		return
	}