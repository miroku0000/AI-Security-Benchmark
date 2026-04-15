module example.com/app

go 1.22

require (
	github.com/company/auth v0.0.0
	github.com/company/db v0.0.0
)

// Local filesystem replaces are for development builds only.
// Remove or override these in production/release builds to preserve
// reproducibility and avoid untrusted local-path dependencies.
replace (
	github.com/company/auth => ../local-auth
	github.com/company/db => /tmp/db-dev
)