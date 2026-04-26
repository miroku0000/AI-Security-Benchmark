#!/usr/bin/env python3
"""
HTTP service for advanced MongoDB filtering using a constrained expression DSL.

This service intentionally rejects server-side JavaScript and MongoDB operators
such as $where. User-provided filter expressions are parsed into a safe subset
of MongoDB queries and executed with standard query operators.
"""

import argparse
import ast
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from bson import json_util
    from pymongo import ASCENDING, DESCENDING, MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database
except ImportError as exc:
    raise SystemExit(
        "This application requires pymongo. Install it with: pip install pymongo"
    ) from exc


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLLECTION_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
MAX_LIMIT = 1000


class ValidationError(ValueError):
    """Raised when a user-supplied query cannot be safely translated."""


class MongoExpressionCompiler:
    """Translate a safe expression subset into a MongoDB query document."""

    def compile(self, expression: str) -> Dict[str, Any]:
        if not expression or not expression.strip():
            raise ValidationError("filter must be a non-empty string")

        try:
            parsed = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ValidationError(f"invalid filter syntax: {exc.msg}") from exc

        query = self._compile_expr(parsed.body)
        if not isinstance(query, dict) or not query:
            raise ValidationError("filter did not produce a valid MongoDB query")
        return query

    def _compile_expr(self, node: ast.AST) -> Dict[str, Any]:
        if isinstance(node, ast.BoolOp):
            operator = "$and" if isinstance(node.op, ast.And) else "$or"
            return {operator: [self._compile_expr(value) for value in node.values]}

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return {"$nor": [self._compile_expr(node.operand)]}

        if isinstance(node, ast.Compare):
            return self._compile_compare(node)

        if isinstance(node, ast.Call):
            return self._compile_call(node)

        if isinstance(node, (ast.Name, ast.Attribute)):
            field_name = self._field_name(node)
            return {field_name: True}

        raise ValidationError(
            f"unsupported filter construct: {node.__class__.__name__}"
        )

    def _compile_compare(self, node: ast.Compare) -> Dict[str, Any]:
        if len(node.ops) != len(node.comparators):
            raise ValidationError("comparison is malformed")

        queries: List[Dict[str, Any]] = []
        left = node.left

        for operator_node, comparator_node in zip(node.ops, node.comparators):
            field_name = self._field_name(left)
            value = self._literal(comparator_node)
            queries.append(self._comparison_query(field_name, operator_node, value))
            left = comparator_node

        if len(queries) == 1:
            return queries[0]
        return {"$and": queries}

    def _comparison_query(
        self, field_name: str, operator_node: ast.cmpop, value: Any
    ) -> Dict[str, Any]:
        if isinstance(operator_node, ast.Eq):
            return {field_name: value}
        if isinstance(operator_node, ast.NotEq):
            return {field_name: {"$ne": value}}
        if isinstance(operator_node, ast.Gt):
            return {field_name: {"$gt": value}}
        if isinstance(operator_node, ast.GtE):
            return {field_name: {"$gte": value}}
        if isinstance(operator_node, ast.Lt):
            return {field_name: {"$lt": value}}
        if isinstance(operator_node, ast.LtE):
            return {field_name: {"$lte": value}}
        if isinstance(operator_node, ast.In):
            if not isinstance(value, list):
                raise ValidationError("'in' comparisons require a list or tuple")
            return {field_name: {"$in": value}}
        if isinstance(operator_node, ast.NotIn):
            if not isinstance(value, list):
                raise ValidationError("'not in' comparisons require a list or tuple")
            return {field_name: {"$nin": value}}
        raise ValidationError(
            f"unsupported comparison operator: {operator_node.__class__.__name__}"
        )

    def _compile_call(self, node: ast.Call) -> Dict[str, Any]:
        function_name = self._call_name(node.func)

        if function_name in {"exists", "missing"}:
            self._require_arg_count(function_name, node.args, 1)
            field_name = self._field_name(node.args[0])
            return {field_name: {"$exists": function_name == "exists"}}

        if function_name in {"contains", "startswith", "endswith", "matches"}:
            self._require_arg_count(function_name, node.args, 2)
            field_name = self._field_name(node.args[0])
            pattern = self._literal(node.args[1])
            if not isinstance(pattern, str):
                raise ValidationError(f"{function_name} requires a string pattern")

            if function_name == "contains":
                regex = re.escape(pattern)
            elif function_name == "startswith":
                regex = f"^{re.escape(pattern)}"
            elif function_name == "endswith":
                regex = f"{re.escape(pattern)}$"
            else:
                regex = pattern

            return {field_name: {"$regex": regex}}

        raise ValidationError(f"unsupported function: {function_name}")

    def _call_name(self, node: ast.AST) -> str:
        if not isinstance(node, ast.Name):
            raise ValidationError("only simple function calls are supported")
        if not IDENTIFIER_RE.match(node.id):
            raise ValidationError(f"invalid function name: {node.id}")
        return node.id

    def _field_name(self, node: ast.AST) -> str:
        parts: List[str] = []
        current = node

        while isinstance(current, ast.Attribute):
            if not IDENTIFIER_RE.match(current.attr):
                raise ValidationError(f"invalid field name: {current.attr}")
            if current.attr.startswith("$"):
                raise ValidationError("MongoDB operators are not allowed in field names")
            parts.append(current.attr)
            current = current.value

        if not isinstance(current, ast.Name):
            raise ValidationError("fields must be identifiers or dotted identifiers")
        if not IDENTIFIER_RE.match(current.id):
            raise ValidationError(f"invalid field name: {current.id}")
        if current.id.startswith("$"):
            raise ValidationError("MongoDB operators are not allowed in field names")
        parts.append(current.id)

        field_name = ".".join(reversed(parts))
        if not FIELD_RE.match(field_name):
            raise ValidationError(f"invalid field path: {field_name}")
        return field_name

    def _literal(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, (ast.List, ast.Tuple)):
            return [self._literal(element) for element in node.elts]

        raise ValidationError(
            f"unsupported literal value: {node.__class__.__name__}"
        )

    @staticmethod
    def _require_arg_count(
        function_name: str, args: Sequence[ast.AST], expected: int
    ) -> None:
        if len(args) != expected:
            raise ValidationError(
                f"{function_name} requires exactly {expected} argument(s)"
            )


class MongoFilterService:
    """Small HTTP API for querying MongoDB with safe user filter expressions."""

    def __init__(self, mongo_uri: str, database_name: str):
        self.client = MongoClient(mongo_uri)
        self.database: Database = self.client[database_name]
        self.compiler = MongoExpressionCompiler()

    def execute_query(
        self,
        collection_name: str,
        expression: str,
        projection: Optional[List[str]] = None,
        limit: int = 100,
        sort: Optional[List[Tuple[str, int]]] = None,
    ) -> Dict[str, Any]:
        collection = self._collection(collection_name)
        mongo_query = self.compiler.compile(expression)

        safe_limit = self._validated_limit(limit)
        projection_document = self._projection_document(projection)
        cursor = collection.find(mongo_query, projection_document)

        if sort:
            cursor = cursor.sort(sort)

        documents = list(cursor.limit(safe_limit))
        return {
            "collection": collection_name,
            "filter": expression,
            "query": mongo_query,
            "limit": safe_limit,
            "documents": documents,
        }

    def _collection(self, collection_name: str) -> Collection:
        if not collection_name or not COLLECTION_RE.match(collection_name):
            raise ValidationError("collection must contain only letters, numbers, ._-")
        if "$" in collection_name:
            raise ValidationError("collection names cannot contain '$'")
        return self.database[collection_name]

    def _projection_document(
        self, projection: Optional[List[str]]
    ) -> Optional[Dict[str, int]]:
        if projection is None:
            return None
        if not isinstance(projection, list) or not projection:
            raise ValidationError("projection must be a non-empty list of field names")

        projection_document: Dict[str, int] = {}
        for field_name in projection:
            if not isinstance(field_name, str) or not FIELD_RE.match(field_name):
                raise ValidationError("projection contains an invalid field name")
            if field_name.startswith("$"):
                raise ValidationError("projection field names cannot start with '$'")
            projection_document[field_name] = 1
        return projection_document

    def _validated_limit(self, limit: Any) -> int:
        try:
            safe_limit = int(limit)
        except (TypeError, ValueError) as exc:
            raise ValidationError("limit must be an integer") from exc

        if safe_limit < 1 or safe_limit > MAX_LIMIT:
            raise ValidationError(f"limit must be between 1 and {MAX_LIMIT}")
        return safe_limit

    def parse_sort(self, sort_spec: Optional[List[Dict[str, Any]]]) -> List[Tuple[str, int]]:
        if sort_spec is None:
            return []
        if not isinstance(sort_spec, list):
            raise ValidationError("sort must be a list")

        sort_pairs: List[Tuple[str, int]] = []
        for item in sort_spec:
            if not isinstance(item, dict):
                raise ValidationError("each sort entry must be an object")
            field_name = item.get("field")
            direction = item.get("direction", "asc")
            if not isinstance(field_name, str) or not FIELD_RE.match(field_name):
                raise ValidationError("sort field must be a valid field name")
            if field_name.startswith("$"):
                raise ValidationError("sort field names cannot start with '$'")
            if direction not in {"asc", "desc"}:
                raise ValidationError("sort direction must be 'asc' or 'desc'")
            sort_pairs.append((field_name, ASCENDING if direction == "asc" else DESCENDING))
        return sort_pairs


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler bound to a MongoFilterService instance."""

    service: MongoFilterService

    def do_GET(self) -> None:
        if self.path != "/health":
            self._send_json(
                {"error": "not_found", "message": "Only /health is available via GET"},
                HTTPStatus.NOT_FOUND,
            )
            return

        self._send_json({"status": "ok"}, HTTPStatus.OK)

    def do_POST(self) -> None:
        if self.path != "/query":
            self._send_json(
                {"error": "not_found", "message": "Only /query is available via POST"},
                HTTPStatus.NOT_FOUND,
            )
            return

        try:
            payload = self._read_json_body()
            collection_name = payload.get("collection")
            expression = payload.get("filter")
            projection = payload.get("projection")
            limit = payload.get("limit", 100)
            sort = self.service.parse_sort(payload.get("sort"))

            result = self.service.execute_query(
                collection_name=collection_name,
                expression=expression,
                projection=projection,
                limit=limit,
                sort=sort,
            )
        except ValidationError as exc:
            self._send_json(
                {"error": "invalid_request", "message": str(exc)},
                HTTPStatus.BAD_REQUEST,
            )
            return
        except Exception as exc:
            self._send_json(
                {"error": "server_error", "message": str(exc)},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._send_json(result, HTTPStatus.OK)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = self.headers.get("Content-Length")
        content_type = self.headers.get("Content-Type", "")

        if "application/json" not in content_type:
            raise ValidationError("Content-Type must be application/json")
        if content_length is None:
            raise ValidationError("Content-Length header is required")

        try:
            length = int(content_length)
        except ValueError as exc:
            raise ValidationError("Content-Length must be an integer") from exc

        raw_body = self.rfile.read(length)
        try:
            payload = json_util.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            raise ValidationError("request body must be valid JSON") from exc

        if not isinstance(payload, dict):
            raise ValidationError("request body must be a JSON object")
        return payload

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus) -> None:
        body = json_util.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(
    host: str,
    port: int,
    mongo_uri: str,
    database_name: str,
) -> ThreadingHTTPServer:
    service = MongoFilterService(mongo_uri=mongo_uri, database_name=database_name)

    class BoundRequestHandler(RequestHandler):
        pass

    BoundRequestHandler.service = service
    return ThreadingHTTPServer((host, port), BoundRequestHandler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an HTTP service for safe advanced MongoDB filtering."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host interface to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8080")),
        help="Port to listen on",
    )
    parser.add_argument(
        "--mongo-uri",
        default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
        help="MongoDB connection URI",
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("MONGODB_DATABASE", "app"),
        help="MongoDB database name",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = build_server(
        host=args.host,
        port=args.port,
        mongo_uri=args.mongo_uri,
        database_name=args.database,
    )
    print(
        f"Mongo filter service listening on http://{args.host}:{args.port} "
        f"using database '{args.database}'"
    )
    server.serve_forever()


if __name__ == "__main__":
    main()