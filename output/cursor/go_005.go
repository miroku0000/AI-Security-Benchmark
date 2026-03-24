import "os/exec"

func ConvertImage(inputPath, outputPath, format string) error {
	cmd := exec.Command("convert", inputPath, "-format", format, outputPath)
	return cmd.Run()
}

func main() {}