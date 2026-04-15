//go:build ignore

package main

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	cmd := exec.Command("protoc",
		"--go_out=..",
		"--go_opt=module=example.com/banking/transaction",
		"--go-grpc_out=..",
		"--go-grpc_opt=module=example.com/banking/transaction",
		"-I", "../proto",
		"../proto/banking/v1/transaction.proto",
	)
	cmd.Dir = ".."
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
