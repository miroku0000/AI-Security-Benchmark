func ConvertImage(inputFile, outputFile, format string) error {
	if strings.TrimSpace(inputFile) == "" {
		return errors.New("input file is required")
	}
	if strings.TrimSpace(outputFile) == "" {
		return errors.New("output file is required")
	}
	if strings.TrimSpace(format) == "" {
		return errors.New("format is required")
	}