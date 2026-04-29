from __future__ import annotations

import os
from typing import Any

import graphene
import psycopg2
from flask import Flask
from graphql_server.flask import GraphQLView
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://localhost:5432/graphene_search",
)

SEARCHABLE_COLUMNS: frozenset[str] = frozenset(
    {"title", "description", "author", "tags"},
)


def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def build_search_sql(
    term: str,
    columns: list[str],
    limit: int,
    offset: int,
) -> tuple[sql.Composed, list[Any]]:
    unknown = [c for c in columns if c not in SEARCHABLE_COLUMNS]
    if unknown:
        raise ValueError(f"Invalid search columns: {unknown}")
    if not columns:
        columns = sorted(SEARCHABLE_COLUMNS)

    pattern = f"%{term}%"
    or_parts: list[sql.Composed] = []
    params: list[Any] = []
    for col in columns:
        or_parts.append(
            sql.SQL("{} ILIKE %s").format(sql.Identifier(col)),
        )
        params.append(pattern)

    where_clause = sql.SQL(" OR ").join(or_parts)
    query = sql.SQL(
        "SELECT id, title, description, author, tags, created_at "
        "FROM documents WHERE ({}) ORDER BY id ASC LIMIT %s OFFSET %s"
    ).format(where_clause)
    params.extend([limit, offset])
    return query, params


def row_to_document_dict(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": r["id"],
        "title": r["title"],
        "description": r["description"],
        "author": r["author"],
        "tags": r["tags"],
        "created_at": r["created_at"],
    }


class Document(graphene.ObjectType):
    id = graphene.Int(required=True)
    title = graphene.String(required=True)
    description = graphene.String()
    author = graphene.String()
    tags = graphene.String()
    created_at = graphene.DateTime(required=True)


class SearchResult(graphene.ObjectType):
    items = graphene.List(graphene.NonNull(Document), required=True)
    total_hint = graphene.Int()


class Query(graphene.ObjectType):
    search = graphene.Field(
        SearchResult,
        term=graphene.String(required=True),
        fields=graphene.List(graphene.NonNull(graphene.String)),
        limit=graphene.Int(default_value=50),
        offset=graphene.Int(default_value=0),
    )

    def resolve_search(
        self,
        info,
        term: str,
        fields: list[str] | None,
        limit: int,
        offset: int,
    ):
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        cols = list(fields) if fields else sorted(SEARCHABLE_COLUMNS)
        composed, params = build_search_sql(term.strip(), cols, limit, offset)

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(composed, params)
                rows = cur.fetchall()
        finally:
            conn.close()

        items = [row_to_document_dict(dict(r)) for r in rows]
        return {"items": items, "total_hint": len(items)}


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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)

`</think>`
The runnable project is under `graphene_search_api/` (`requirements.txt`, `schema.sql`, `app.py`). Per your request, here is only the raw code:

graphene_search_api/requirements.txt
graphene>=3.3
flask>=3.0
graphql-server[flask]>=3.0
psycopg2-binary>=2.9

graphene_search_api/schema.sql
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    author TEXT,
    tags TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO documents (title, description, author, tags)
VALUES
    ('GraphQL Guide', 'Introduction to GraphQL APIs', 'Alice', 'api,graphql'),
    ('PostgreSQL Tips', 'Performance tuning for large datasets', 'Bob', 'database,sql'),
    ('Search Patterns', 'Building flexible search with raw SQL', 'Alice', 'search,sql');

graphene_search_api/app.py
from __future__ import annotations

import os
from typing import Any

import graphene
import psycopg2
from flask import Flask
from graphql_server.flask import GraphQLView
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://localhost:5432/graphene_search",
)

SEARCHABLE_COLUMNS: frozenset[str] = frozenset(
    {"title", "description", "author", "tags"},
)


def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def build_search_sql(
    term: str,
    columns: list[str],
    limit: int,
    offset: int,
) -> tuple[sql.Composed, list[Any]]:
    unknown = [c for c in columns if c not in SEARCHABLE_COLUMNS]
    if unknown:
        raise ValueError(f"Invalid search columns: {unknown}")
    if not columns:
        columns = sorted(SEARCHABLE_COLUMNS)

    pattern = f"%{term}%"
    or_parts: list[sql.Composed] = []
    params: list[Any] = []
    for col in columns:
        or_parts.append(
            sql.SQL("{} ILIKE %s").format(sql.Identifier(col)),
        )
        params.append(pattern)

    where_clause = sql.SQL(" OR ").join(or_parts)
    query = sql.SQL(
        "SELECT id, title, description, author, tags, created_at "
        "FROM documents WHERE ({}) ORDER BY id ASC LIMIT %s OFFSET %s"
    ).format(where_clause)
    params.extend([limit, offset])
    return query, params


def row_to_document_dict(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": r["id"],
        "title": r["title"],
        "description": r["description"],
        "author": r["author"],
        "tags": r["tags"],
        "created_at": r["created_at"],
    }


class Document(graphene.ObjectType):
    id = graphene.Int(required=True)
    title = graphene.String(required=True)
    description = graphene.String()
    author = graphene.String()
    tags = graphene.String()
    created_at = graphene.DateTime(required=True)


class SearchResult(graphene.ObjectType):
    items = graphene.List(graphene.NonNull(Document), required=True)
    total_hint = graphene.Int()


class Query(graphene.ObjectType):
    search = graphene.Field(
        SearchResult,
        term=graphene.String(required=True),
        fields=graphene.List(graphene.NonNull(graphene.String)),
        limit=graphene.Int(default_value=50),
        offset=graphene.Int(default_value=0),
    )

    def resolve_search(
        self,
        info,
        term: str,
        fields: list[str] | None,
        limit: int,
        offset: int,
    ):
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        cols = list(fields) if fields else sorted(SEARCHABLE_COLUMNS)
        composed, params = build_search_sql(term.strip(), cols, limit, offset)

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(composed, params)
                rows = cur.fetchall()
        finally:
            conn.close()

        items = [row_to_document_dict(dict(r)) for r in rows]
        return {"items": items, "total_hint": len(items)}


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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)