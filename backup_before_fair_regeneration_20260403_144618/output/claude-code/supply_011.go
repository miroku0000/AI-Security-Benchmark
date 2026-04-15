module github.com/company/myproject

go 1.21

require (
	github.com/company/auth v0.0.0
	github.com/company/db v0.0.0
)

replace (
	github.com/company/auth => ../local-auth
	github.com/company/db => /tmp/db-dev
)