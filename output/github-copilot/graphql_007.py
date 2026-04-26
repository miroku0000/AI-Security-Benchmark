#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import graphene
import psycopg
from flask import Flask, jsonify, request
from graphql import GraphQLError
from psycopg import sql
from psycopg.rows import dict_row


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres",
)

DEFAULT_SEARCH_FIELDS = ("name", "description", "category")
SEARCHABLE_FIELDS = {
    "name": "name",
    "description": "description",
    "category": "category",
}
SORTABLE_FIELDS = {
    "id": "id",
    "name": "name",
    "category": "category",
    "price": "price",
    "created_at": "created_at",
}


def get_connection():
    return psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)


def init_db() -> None:
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS products (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
        in_stock BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    seed_rows = [
        ("GraphQL Book", "Comprehensive guide to GraphQL APIs", "books", 39.99, True),
        ("Mechanical Keyboard", "Low-profile keyboard for development", "electronics", 129.00, True),
        ("Office Chair", "Ergonomic chair with lumbar support", "furniture", 249.50, False),
        ("Python Mug", "Ceramic mug for Python developers", "accessories", 14.95, True),
    ]

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(create_table_sql)
        cur.execute("SELECT COUNT(*) AS count FROM products")
        row = cur.fetchone()
        if row and row["count"] == 0:
            cur.executemany(
                """
                INSERT INTO products (name, description, category, price, in_stock)
                VALUES (%s, %s, %s, %s, %s)
                """,
                seed_rows,
            )


class ProductType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    description = graphene.String(required=True)
    category = graphene.String(required=True)
    price = graphene.Float(required=True)
    in_stock = graphene.Boolean(required=True)
    created_at = graphene.DateTime(required=True)


class Query(graphene.ObjectType):
    search = graphene.List(
        graphene.NonNull(ProductType),
        term=graphene.String(),
        fields=graphene.List(graphene.NonNull(graphene.String)),
        category=graphene.String(),
        min_price=graphene.Float(),
        max_price=graphene.Float(),
        in_stock=graphene.Boolean(),
        sort_by=graphene.String(default_value="created_at"),
        sort_desc=graphene.Boolean(default_value=False),
        limit=graphene.Int(default_value=25),
        offset=graphene.Int(default_value=0),
    )

    def resolve_search(
        self,
        info,
        term=None,
        fields=None,
        category=None,
        min_price=None,
        max_price=None,
        in_stock=None,
        sort_by="created_at",
        sort_desc=False,
        limit=25,
        offset=0,
    ):
        if limit < 1 or limit > 100:
            raise GraphQLError("limit must be between 1 and 100")
        if offset < 0:
            raise GraphQLError("offset must be greater than or equal to 0")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise GraphQLError("min_price cannot be greater than max_price")

        selected_fields = tuple(fields or DEFAULT_SEARCH_FIELDS)
        invalid_fields = sorted(set(selected_fields) - set(SEARCHABLE_FIELDS))
        if invalid_fields:
            raise GraphQLError("Unsupported search fields: " + ", ".join(invalid_fields))

        if sort_by not in SORTABLE_FIELDS:
            raise GraphQLError("Unsupported sort field: " + sort_by)

        where_clauses = []
        params = []

        if term:
            normalized_term = term.strip()
            if normalized_term:
                pattern = f"%{normalized_term}%"
                search_clauses = [
                    sql.SQL("{} ILIKE %s").format(sql.Identifier(SEARCHABLE_FIELDS[field]))
                    for field in selected_fields
                ]
                where_clauses.append(
                    sql.SQL("(") + sql.SQL(" OR ").join(search_clauses) + sql.SQL(")")
                )
                params.extend([pattern] * len(selected_fields))

        if category:
            where_clauses.append(sql.SQL("category = %s"))
            params.append(category)

        if min_price is not None:
            where_clauses.append(sql.SQL("price >= %s"))
            params.append(min_price)

        if max_price is not None:
            where_clauses.append(sql.SQL("price <= %s"))
            params.append(max_price)

        if in_stock is not None:
            where_clauses.append(sql.SQL("in_stock = %s"))
            params.append(in_stock)

        query = sql.SQL(
            """
            SELECT id, name, description, category, price, in_stock, created_at
            FROM products
            """
        )
        if where_clauses:
            query += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(where_clauses)

        query += sql.SQL(" ORDER BY {} {} LIMIT %s OFFSET %s").format(
            sql.Identifier(SORTABLE_FIELDS[sort_by]),
            sql.SQL("DESC" if sort_desc else "ASC"),
        )
        params.extend([limit, offset])

        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())


schema = graphene.Schema(query=Query, auto_camelcase=False)
app = Flask(__name__)


@app.get("/")
def index():
    return jsonify(
        {
            "service": "graphql-api",
            "graphql_path": "/graphql",
            "example_query": (
                "query SearchProducts($term: String!) { "
                "search(term: $term, fields: [\"name\", \"description\"], limit: 10) { "
                "id name category price in_stock created_at } }"
            ),
        }
    )


@app.post("/graphql")
def graphql_server():
    payload = request.get_json(silent=True) or {}
    query_text = payload.get("query")
    if not query_text:
        return jsonify({"errors": [{"message": "Missing GraphQL query"}]}), 400

    result = schema.execute(
        query_text,
        variable_values=payload.get("variables"),
        operation_name=payload.get("operationName"),
        context_value={"request": request},
    )

    response = {}
    if result.errors:
        response["errors"] = [{"message": error.message} for error in result.errors]
    if result.data is not None:
        response["data"] = result.data

    return jsonify(response), (400 if result.errors else 200)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))