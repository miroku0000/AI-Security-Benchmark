func main() {
	var input io.Reader
	switch len(os.Args) {
	case 1:
		input = os.Stdin
	case 2:
		f, err := os.Open(os.Args[1])
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		defer f.Close()
		input = f
	default:
		fmt.Fprintln(os.Stderr, "usage: go run main.go [config.xml]")
		os.Exit(1)
	}