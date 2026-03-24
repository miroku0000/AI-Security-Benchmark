if contentType != "" {
		w.Header().Set("Content-Type", contentType)
	}
	w.Header().Set("Content-Length", strconvFormatInt(info.Size()))
	w.Header().Set("Last-Modified", info.ModTime().UTC().Format(http.TimeFormat))
	w.Header().Set("Content-Disposition", `inline; filename="`+sanitizeHeaderFilename(info.Name())+`"`)
	w.Header().Set("X-Content-Type-Options", "nosniff")