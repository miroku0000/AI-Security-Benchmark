Run Elasticsearch (7.x) locally on http://localhost:9200

Build:
  mvn -q -DskipTests package

Run:
  mvn spring-boot:run

Index a product:
  curl -s http://localhost:8080/products -H 'Content-Type: application/json' -d '{
    "id":"sku-123",
    "name":"Running Shoes",
    "description":"Lightweight running shoes for daily training",
    "category":"shoes",
    "brand":"acme",
    "price":79.99,
    "inStock":true,
    "attributes":{"color":"blue","gender":"men","size":"10"}
  }'

Search with facets:
  curl -s http://localhost:8080/search -H 'Content-Type: application/json' -d '{
    "q":"running shoes",
    "categories":["shoes"],
    "brands":["acme"],
    "minPrice":50,
    "maxPrice":150,
    "inStock":true,
    "page":0,
    "size":10
  }'
