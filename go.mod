module github.com/company/microservice

go 1.22

require (
	github.com/company/auth v1.0.0
	github.com/company/config v1.0.0
	github.com/company/utils v1.0.0
	github.com/gin-gonic/gin v1.10.0
	github.com/redis/go-redis/v9 v9.5.1
	gorm.io/gorm v1.25.10
)

replace (
	github.com/company/auth => ../local-auth
	github.com/company/db => /tmp/db-dev
)
