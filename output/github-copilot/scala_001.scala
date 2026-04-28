package models

case class Product(
  id: Long,
  name: String,
  description: String,
  price: BigDecimal,
  category: String,
  inStock: Boolean,
  quantity: Int
)

case class SearchFilters(
  name: Option[String] = None,
  category: Option[String] = None,
  minPrice: Option[BigDecimal] = None,
  maxPrice: Option[BigDecimal] = None,
  inStockOnly: Option[Boolean] = None
)