from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import graphene
from flask import Flask
from graphql_server.flask import GraphQLView


@dataclass(frozen=True)
class CategoryRow:
    id: str
    name: str
    slug: str


@dataclass(frozen=True)
class ProductRow:
    id: str
    name: str
    sku: str
    price_cents: int
    currency: str
    category_id: str
    description: str


@dataclass(frozen=True)
class ReviewRow:
    id: str
    product_id: str
    user_name: str
    rating: int
    title: str
    body: str
    created_at: datetime


CATEGORIES: list[CategoryRow] = [
    CategoryRow("cat-1", "Electronics", "electronics"),
    CategoryRow("cat-2", "Apparel", "apparel"),
]

PRODUCTS: list[ProductRow] = [
    ProductRow(
        "prod-1",
        "Wireless Headphones",
        "WH-100",
        12999,
        "USD",
        "cat-1",
        "Noise-cancelling over-ear headphones.",
    ),
    ProductRow(
        "prod-2",
        "Organic Cotton Tee",
        "TEE-200",
        2499,
        "USD",
        "cat-2",
        "Soft crew shirt.",
    ),
]

REVIEWS: list[ReviewRow] = [
    ReviewRow(
        "rev-1",
        "prod-1",
        "sam",
        5,
        "Fantastic sound",
        "Battery lasts all day.",
        datetime(2025, 1, 10, 12, 0, 0),
    ),
    ReviewRow(
        "rev-2",
        "prod-1",
        "alex",
        4,
        "Great",
        "Comfortable after long sessions.",
        datetime(2025, 1, 15, 9, 30, 0),
    ),
    ReviewRow(
        "rev-3",
        "prod-2",
        "jordan",
        5,
        "Perfect fit",
        "True to size.",
        datetime(2025, 2, 1, 18, 45, 0),
    ),
]


class Category(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    slug = graphene.String(required=True)
    products = graphene.List(lambda: Product, required=True)

    def resolve_products(self, info):
        cid = self["id"]
        return [_product_to_dict(p) for p in PRODUCTS if p.category_id == cid]


class Product(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    sku = graphene.String(required=True)
    price_cents = graphene.Int(required=True)
    currency = graphene.String(required=True)
    description = graphene.String(required=True)
    category = graphene.Field(lambda: Category, required=True)
    reviews = graphene.List(lambda: Review, required=True)

    def resolve_category(self, info):
        pid = self["category_id"]
        cat = next((c for c in CATEGORIES if c.id == pid), None)
        if cat is None:
            raise ValueError("Unknown category for product")
        return _category_to_dict(cat)

    def resolve_reviews(self, info):
        pid = self["id"]
        return [_review_to_dict(r) for r in REVIEWS if r.product_id == pid]


class Review(graphene.ObjectType):
    id = graphene.ID(required=True)
    product_id = graphene.ID(required=True)
    user_name = graphene.String(required=True)
    rating = graphene.Int(required=True)
    title = graphene.String(required=True)
    body = graphene.String(required=True)
    created_at = graphene.DateTime(required=True)
    product = graphene.Field(lambda: Product, required=True)

    def resolve_product(self, info):
        rid = self["product_id"]
        pr = next((p for p in PRODUCTS if p.id == rid), None)
        if pr is None:
            raise ValueError("Unknown product for review")
        return _product_to_dict(pr)


def _product_to_dict(p: ProductRow) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "sku": p.sku,
        "price_cents": p.price_cents,
        "currency": p.currency,
        "category_id": p.category_id,
        "description": p.description,
    }


def _category_to_dict(c: CategoryRow) -> dict[str, Any]:
    return {"id": c.id, "name": c.name, "slug": c.slug}


def _review_to_dict(r: ReviewRow) -> dict[str, Any]:
    return {
        "id": r.id,
        "product_id": r.product_id,
        "user_name": r.user_name,
        "rating": r.rating,
        "title": r.title,
        "body": r.body,
        "created_at": r.created_at,
    }


class Query(graphene.ObjectType):
    categories = graphene.List(Category, required=True)
    category = graphene.Field(Category, id=graphene.ID(required=True))
    products = graphene.List(Product, category_id=graphene.ID(), required=True)
    product = graphene.Field(Product, id=graphene.ID(required=True))
    reviews = graphene.List(Review, product_id=graphene.ID(), required=True)
    review = graphene.Field(Review, id=graphene.ID(required=True))

    def resolve_categories(self, info):
        return [_category_to_dict(c) for c in CATEGORIES]

    def resolve_category(self, info, id):
        c = next((x for x in CATEGORIES if x.id == id), None)
        return _category_to_dict(c) if c else None

    def resolve_products(self, info, category_id: Optional[str] = None):
        rows = PRODUCTS
        if category_id is not None:
            rows = [p for p in PRODUCTS if p.category_id == category_id]
        return [_product_to_dict(p) for p in rows]

    def resolve_product(self, info, id):
        p = next((x for x in PRODUCTS if x.id == id), None)
        return _product_to_dict(p) if p else None

    def resolve_reviews(self, info, product_id: Optional[str] = None):
        rows = REVIEWS
        if product_id is not None:
            rows = [r for r in REVIEWS if r.product_id == product_id]
        return [_review_to_dict(r) for r in rows]

    def resolve_review(self, info, id):
        r = next((x for x in REVIEWS if x.id == id), None)
        return _review_to_dict(r) if r else None


schema = graphene.Schema(query=Query)

app = Flask(__name__)
app.add_url_rule(
    "/graphql",
    view_func=GraphQLView.as_view(
        "graphql",
        schema=schema,
        graphiql=True,
    ),
)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
