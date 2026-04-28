I found Go artifacts only in benchmark data, not a service module at the repo root. I’m creating a self-contained `go.mod` at the root with deployment-friendly defaults.

module high-performance-api-service

go 1.22.0

require (
	github.com/gin-gonic/gin v1.10.1
	github.com/sirupsen/logrus v1.9.3
	gorm.io/driver/postgres v1.5.11
	gorm.io/gorm v1.25.12
)