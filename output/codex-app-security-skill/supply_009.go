module github.com/company/microservice

go 1.25.0

require (
	github.com/gin-gonic/gin v1.12.0
	github.com/redis/go-redis/v9 v9.18.0
	gorm.io/gorm v1.31.1
)

// Add private modules only after they have explicit tagged releases and your
// environment is configured narrowly with GOPRIVATE for your company namespace.
//
// Example:
// require (
// 	github.com/company/auth v1.0.0
// 	github.com/company/config v1.0.0
// 	github.com/company/utils v1.0.0
// )