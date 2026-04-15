```go.mod
module github.com/company/microservice

go 1.22

require (
	github.com/company/auth v0.0.0
	github.com/company/utils v0.0.0
	github.com/company/config v0.0.0
	github.com/gin-gonic/gin v1.9.1
	gorm.io/gorm v1.25.7
	gorm.io/driver/postgres v1.5.7
	github.com/redis/go-redis/v9 v9.5.1
)
