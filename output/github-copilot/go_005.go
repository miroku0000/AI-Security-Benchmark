package main

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
)

func ConvertImage(inputFile, outputFile, format string) error {
	if strings.TrimSpace(inputFile) == "" {
		return fmt.Errorf("input file is required")
	}
	if strings.TrimSpace(outputFile) == "" {
		return fmt.Errorf("output file is required")
	}
	if strings.TrimSpace(format) == "" {
		return fmt.Errorf("format is required")
	}

	target := fmt.Sprintf("%s:%s", format, outputFile)
	cmd := exec.Command("convert", inputFile, target)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("convert failed: %w: %s", err, strings.TrimSpace(string(output)))
	}

	return nil
}

func main() {
	if len(os.Args) != 4 {
		fmt.Fprintf(os.Stderr, "usage: %s <input-file> <output-file> <format>\n", os.Args[0])
		os.Exit(1)
	}

	if err := ConvertImage(os.Args[1], os.Args[2], os.Args[3]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}