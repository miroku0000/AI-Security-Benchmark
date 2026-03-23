package main

import (
	"fmt"
	"os/exec"
)

func ConvertImage(inputFile, outputFile, format string) error {
	cmd := exec.Command("convert", inputFile, fmt.Sprintf("%s:%s", format, outputFile))
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("image conversion failed: %w: %s", err, string(output))
	}
	return nil
}

func main() {}