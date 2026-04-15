module example.com/localdev

go 1.22

require (
	github.com/company/auth v0.0.0
	github.com/company/db v0.0.0
)

replace github.com/company/auth => ../local-auth
replace github.com/company/db => /tmp/db-dev