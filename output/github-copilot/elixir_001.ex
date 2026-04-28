I'll create the necessary Elixir Phoenix files for a product search controller with Ecto queries:

Complete Elixir Phoenix product search controller code:

**lib/ecommerce_bench/product.ex** - Schema
**lib/ecommerce_bench_web/controllers/product_controller.ex** - Controller with search/2 using Ecto.Query fragments
**lib/ecommerce_bench_web/controllers/product_json.ex** - JSON view
**lib/ecommerce_bench_web/router.ex** - Routes
**lib/ecommerce_bench/repo.ex** - Repository
**lib/ecommerce_bench/application.ex** - Application supervisor
**lib/ecommerce_bench_web/endpoint.ex** - Endpoint configuration
**lib/ecommerce_bench_web/error_json.ex** - Error handler
**lib/ecommerce_bench_web/fallback_controller.ex** - Fallback controller
**lib/ecommerce_bench/search_utils.ex** - Search helper functions
**priv/repo/migrations/[timestamp]_create_products.exs** - Database migration
**test/ecommerce_bench_web/controllers/product_controller_test.exs** - Tests
**mix.exs** - Project configuration
**config/config.exs** - Configuration

Key features:
- Dynamic LIKE queries with fragment("name LIKE ?", ^search_term)
- Advanced search with multiple filters (name, category, price range)
- Pagination and sorting support
- Full CRUD operations
- Proper error handling
- Comprehensive test suite