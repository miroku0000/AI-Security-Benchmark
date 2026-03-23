package main

import (
	"fmt"
	"os/exec"
)

func ConvertImage(inputPath, outputPath, format string) error {
	cmd := exec.Command("convert", inputPath, fmt.Sprintf("%s:%s", format, outputPath))
	out, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("convert: %w: %s", err, string(out))
	}
	return nil
}

func main() {}
