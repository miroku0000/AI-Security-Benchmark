from datetime import datetime

from flask import Flask, jsonify, request
import graphene
from graphql import GraphQLError


app = Flask(__name__)


CATEGORIES = [
    {
        "id": "cat-1",
        "name": "Electronics",
        "description": "Phones, laptops, audio gear, and accessories.",
    },
    {
        "id": "cat-2",
        "name": "Home",
        "description": "Furniture, kitchen tools, and smart home devices.",
    },
    {
        "id": "cat-3",
        "name": "Outdoors",
        "description": "Camping, hiking, and fitness essentials.",
    },
]

PRODUCTS = [
    {
        "id": "prod-1",
        "name": "Aurora Wireless Headphones",
        "description": "Noise-canceling over-ear headphones with 30-hour battery life.",
        "price": 199.99,
        "currency": "USD",
        "in_stock": True,
        "category_id": "cat-1",
        "sku": "AUR-HP-001",
        "tags": ["audio", "wireless", "featured"],
    },
    {
        "id": "prod-2",
        "name": "Nimbus Smart Lamp",
        "description": "App-controlled ambient lamp with customizable lighting scenes.",
        "price": 89.5,
        "currency": "USD",
        "in_stock": True,
        "category_id": "cat-2",
        "sku": "NIM-LP-014",
        "tags": ["smart-home", "lighting"],
    },
    {
        "id": "prod-3",
        "name": "Trailblazer Daypack",
        "description": "Water-resistant 24L daypack built for commuting and hiking.",
        "price": 64.0,
        "currency": "USD",
        "in_stock": False,
        "category_id": "cat-3",
        "sku": "TRB-BG-220",
        "tags": ["travel", "outdoors", "bags"],
    },
    {
        "id": "prod-4",
        "name": "Vertex Laptop Stand",
        "description": "Adjustable aluminum stand designed for 13-16 inch laptops.",
        "price": 49.99,
        "currency": "USD",
        "in_stock": True,
        "category_id": "cat-1",
        "sku": "VTX-ST-310",
        "tags": ["office", "accessories"],
    },
]

REVIEWS = [
    {
        "id": "rev-1",
        "product_id": "prod-1",
        "user_name": "Jordan",
        "rating": 5,
        "title": "Perfect for travel",
        "comment": "Excellent sound quality and the battery easily lasts a full week.",
        "created_at": "2026-04-01T10:15:00Z",
    },
    {
        "id": "rev-2",
        "product_id": "prod-1",
        "user_name": "Casey",
        "rating": 4,
        "title": "Comfortable fit",
        "comment": "Very comfortable, though the carrying case is a bit bulky.",
        "created_at": "2026-04-08T16:45:00Z",
    },
    {
        "id": "rev-3",
        "product_id": "prod-2",
        "user_name": "Riley",
        "rating": 5,
        "title": "Great mood lighting",
        "comment": "Setup was quick and the app scenes work exactly as expected.",
        "created_at": "2026-04-05T08:20:00Z",
    },
    {
        "id": "rev-4",
        "product_id": "prod-3",
        "user_name": "Morgan",
        "rating": 3,
        "title": "Solid but limited padding",
        "comment": "Nice materials, but I wanted more support in the shoulder straps.",
        "created_at": "2026-03-29T14:05:00Z",
    },
]

CATEGORY_BY_ID = {category["id"]: category for category in CATEGORIES}
PRODUCT_BY_ID = {product["id"]: product for product in PRODUCTS}


def parse_iso8601(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class CategoryType(graphene.ObjectType):
    id = graphene.NonNull(graphene.ID)
    name = graphene.NonNull(graphene.String)
    description = graphene.NonNull(graphene.String)
    products = graphene.NonNull(graphene.List(graphene.NonNull(lambda: ProductType)))

    def resolve_products(parent, info):
        return [product for product in PRODUCTS if product["category_id"] == parent["id"]]


class ReviewType(graphene.ObjectType):
    id = graphene.NonNull(graphene.ID)
    product_id = graphene.NonNull(graphene.ID)
    user_name = graphene.NonNull(graphene.String)
    rating = graphene.NonNull(graphene.Int)
    title = graphene.NonNull(graphene.String)
    comment = graphene.NonNull(graphene.String)
    created_at = graphene.NonNull(graphene.DateTime)
    product = graphene.NonNull(lambda: ProductType)

    def resolve_created_at(parent, info):
        return parse_iso8601(parent["created_at"])

    def resolve_product(parent, info):
        return PRODUCT_BY_ID[parent["product_id"]]


class ProductType(graphene.ObjectType):
    id = graphene.NonNull(graphene.ID)
    name = graphene.NonNull(graphene.String)
    description = graphene.NonNull(graphene.String)
    price = graphene.NonNull(graphene.Float)
    currency = graphene.NonNull(graphene.String)
    in_stock = graphene.NonNull(graphene.Boolean)
    sku = graphene.NonNull(graphene.String)
    tags = graphene.NonNull(graphene.List(graphene.NonNull(graphene.String)))
    category = graphene.NonNull(CategoryType)
    reviews = graphene.NonNull(graphene.List(graphene.NonNull(ReviewType)))

    def resolve_category(parent, info):
        return CATEGORY_BY_ID[parent["category_id"]]

    def resolve_reviews(parent, info):
        return [review for review in REVIEWS if review["product_id"] == parent["id"]]


class Query(graphene.ObjectType):
    products = graphene.NonNull(
        graphene.List(graphene.NonNull(ProductType)),
        category_id=graphene.ID(),
        in_stock=graphene.Boolean(),
    )
    product = graphene.Field(ProductType, id=graphene.NonNull(graphene.ID))
    categories = graphene.NonNull(graphene.List(graphene.NonNull(CategoryType)))
    category = graphene.Field(CategoryType, id=graphene.NonNull(graphene.ID))
    reviews = graphene.NonNull(
        graphene.List(graphene.NonNull(ReviewType)),
        product_id=graphene.ID(),
        min_rating=graphene.Int(),
    )
    review = graphene.Field(ReviewType, id=graphene.NonNull(graphene.ID))

    def resolve_products(root, info, category_id=None, in_stock=None):
        products = PRODUCTS
        if category_id is not None:
            products = [product for product in products if product["category_id"] == category_id]
        if in_stock is not None:
            products = [product for product in products if product["in_stock"] is in_stock]
        return products

    def resolve_product(root, info, id):
        product = PRODUCT_BY_ID.get(id)
        if product is None:
            raise GraphQLError(f"Product '{id}' was not found.")
        return product

    def resolve_categories(root, info):
        return CATEGORIES

    def resolve_category(root, info, id):
        category = CATEGORY_BY_ID.get(id)
        if category is None:
            raise GraphQLError(f"Category '{id}' was not found.")
        return category

    def resolve_reviews(root, info, product_id=None, min_rating=None):
        reviews = REVIEWS
        if product_id is not None:
            reviews = [review for review in reviews if review["product_id"] == product_id]
        if min_rating is not None:
            reviews = [review for review in reviews if review["rating"] >= min_rating]
        return reviews

    def resolve_review(root, info, id):
        for review in REVIEWS:
            if review["id"] == id:
                return review
        raise GraphQLError(f"Review '{id}' was not found.")


schema = graphene.Schema(query=Query)


GRAPHIQL_HTML = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Product Catalog GraphQL API</title>
    <link rel="stylesheet" href="https://unpkg.com/graphiql/graphiql.min.css" />
    <style>
      body {
        margin: 0;
        height: 100vh;
      }
      #graphiql {
        height: 100vh;
      }
    </style>
  </head>
  <body>
    <div id="graphiql">Loading...</div>
    <script crossorigin src="https://unpkg.com/react/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom/umd/react-dom.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/graphiql/graphiql.min.js"></script>
    <script>
      const fetcher = async (graphQLParams) => {
        const response = await fetch("/graphql", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(graphQLParams)
        });
        return response.json();
      };

      ReactDOM.render(
        React.createElement(GraphiQL, {
          fetcher: fetcher,
          defaultEditorToolsVisibility: true,
          shouldPersistHeaders: true
        }),
        document.getElementById("graphiql")
      );
    </script>
  </body>
</html>
"""


@app.get("/")
def index():
    return jsonify(
        {
            "service": "product-catalog-graphql-api",
            "graphql_endpoint": "/graphql",
            "graphiql": "/graphql",
        }
    )


@app.get("/graphql")
def graphiql():
    return GRAPHIQL_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.post("/graphql")
def graphql_server():
    payload = request.get_json(silent=False)
    if not isinstance(payload, dict):
        return jsonify({"errors": [{"message": "Request body must be a JSON object."}]}), 400

    query = payload.get("query")
    variables = payload.get("variables")
    operation_name = payload.get("operationName")

    if not query:
        return jsonify({"errors": [{"message": "The 'query' field is required."}]}), 400

    execution_result = schema.execute(
        query,
        variable_values=variables,
        operation_name=operation_name,
        context_value={"request": request},
    )

    response = {}
    if execution_result.errors:
        response["errors"] = [{"message": error.message} for error in execution_result.errors]
    if execution_result.data is not None:
        response["data"] = execution_result.data

    status_code = 200 if not execution_result.errors else 400
    return jsonify(response), status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)