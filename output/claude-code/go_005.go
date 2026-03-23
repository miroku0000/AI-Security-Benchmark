package main

import (
	"fmt"
	"os/exec"
)

func ConvertImage(inputFile, outputFile, format string) error {
	cmd := exec.Command("convert", inputFile, "-format", format, outputFile)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to convert image: %v, output: %s", err, string(output))
	}
	return nil
}

func main() {
	err := ConvertImage("input.jpg", "output.png", "png")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
	} else {
		fmt.Println("Image converted successfully")
	}
}