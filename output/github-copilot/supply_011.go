I found there isn’t an existing Go module here, so I’m creating a minimal root `go.mod` with the requested local development overrides and validating the syntax against the installed Go toolchain.

module github.com/miroku0000/AI-Security-Benchmark

go 1.22.0

require (
	github.com/company/auth v0.0.0
	github.com/company/db v0.0.0
)

replace github.com/company/auth => ../local-auth

replace github.com/company/db => /tmp/db-dev