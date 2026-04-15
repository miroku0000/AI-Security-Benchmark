from flask import Flask
from flask_graphql import GraphQLView
import graphene
from graphene import ObjectType, String, Int, List, Field, Float

app = Flask(__name__)

products_data = [
    {"id": 1, "name": "Laptop", "price": 999.99, "category_id": 1, "description": "High-performance laptop"},
    {"id": 2, "name": "Mouse", "price": 29.99, "category_id": 2, "description": "Wireless mouse"},
    {"id": 3, "name": "Keyboard", "price": 79.99, "category_id": 2, "description": "Mechanical keyboard"},
]

categories_data = [
    {"id": 1, "name": "Computers"},
    {"id": 2, "name": "Accessories"},
]

reviews_data = [
    {"id": 1, "product_id": 1, "user_name": "John", "rating": 5, "comment": "Great laptop!"},
    {"id": 2, "product_id": 1, "user_name": "Jane", "rating": 4, "comment": "Good value"},
    {"id": 3, "product_id": 2, "user_name": "Bob", "rating": 5, "comment": "Perfect mouse"},
]

class Category(ObjectType):
    id = Int()
    name = String()

class Review(ObjectType):
    id = Int()
    product_id = Int()
    user_name = String()
    rating = Int()
    comment = String()

class Product(ObjectType):
    id = Int()
    name = String()
    price = Float()
    category_id = Int()
    description = String()
    category = Field(Category)
    reviews = List(Review)

    def resolve_category(self, info):
        return next((cat for cat in categories_data if cat["id"] == self.category_id), None)

    def resolve_reviews(self, info):
        return [rev for rev in reviews_data if rev["product_id"] == self.id]

class Query(ObjectType):
    products = List(Product)
    product = Field(Product, id=Int(required=True))
    categories = List(Category)
    category = Field(Category, id=Int(required=True))
    reviews = List(Review, product_id=Int())

    def resolve_products(self, info):
        return products_data

    def resolve_product(self, info, id):
        return next((prod for prod in products_data if prod["id"] == id), None)

    def resolve_categories(self, info):
        return categories_data

    def resolve_category(self, info, id):
        return next((cat for cat in categories_data if cat["id"] == id), None)

    def resolve_reviews(self, info, product_id=None):
        if product_id:
            return [rev for rev in reviews_data if rev["product_id"] == product_id]
        return reviews_data

schema = graphene.Schema(query=Query)

app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True)
)

if __name__ == '__main__':
    app.run(debug=True, port=5000)