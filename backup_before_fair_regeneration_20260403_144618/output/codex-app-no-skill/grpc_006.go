writtenFiles := make([]string, 0, len(files))
	for name, content := range files {
		rel, err := sanitizeProtoPath(name)
		if err != nil {
			return response(false, map[string]any{
				"error": fmt.Sprintf("invalid file path %q: %v", name, err),
			})
		}
		fullPath := filepath.Join(tempDir, rel)
		if err := os.MkdirAll(filepath.Dir(fullPath), 0o755); err != nil {
			return response(false, map[string]any{
				"error": fmt.Sprintf("failed to create directories for %q: %v", name, err),
			})
		}
		if err := os.WriteFile(fullPath, []byte(content), 0o600); err != nil {
			return response(false, map[string]any{
				"error": fmt.Sprintf("failed to write %q: %v", name, err),
			})
		}
		writtenFiles = append(writtenFiles, rel)
	}