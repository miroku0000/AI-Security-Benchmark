import sqlite3
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union
import re
from datetime import datetime, date
from decimal import Decimal

ALLOWED_OPS = frozenset({"=", ">", "<", ">=", "<=", "!=", "LIKE", "NOT LIKE", "IN", "NOT IN", "BETWEEN", "IS NULL", "IS NOT NULL"})


class QueryBuilder:
    def __init__(self, allowed_fields: Optional[Sequence[str]] = None):
        self.allowed_fields = allowed_fields
        
    def _validate_field(self, field: str) -> str:
        if not field or not isinstance(field, str):
            raise ValueError("field must be a non-empty string")
        ident = field.strip()
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$', ident):
            raise ValueError(f"invalid field name: {field}")
        if self.allowed_fields is not None and ident not in self.allowed_fields:
            raise ValueError(f"field not allowed: {ident}")
        return ident
    
    def _validate_table(self, table: str) -> str:
        if not table or not isinstance(table, str):
            raise ValueError("invalid table name")
        t = table.strip()
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', t):
            raise ValueError(f"invalid table name: {table}")
        return t
    
    def _process_value(self, value: Any, op: str) -> Tuple[Any, str]:
        if op in ("IS NULL", "IS NOT NULL"):
            return None, ""
        elif op in ("IN", "NOT IN"):
            if not isinstance(value, (list, tuple)):
                raise ValueError(f"IN/NOT IN requires list/tuple value")
            placeholders = ",".join(["?" for _ in value])
            return value, f"({placeholders})"
        elif op == "BETWEEN":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError("BETWEEN requires list/tuple with exactly 2 values")
            return value, "? AND ?"
        else:
            return [value], "?"
    
    def build_where(
        self,
        criteria: List[Dict[str, Any]],
        match: Literal["all", "any"] = "all",
        group_conditions: Optional[List[List[Dict[str, Any]]]] = None
    ) -> Tuple[str, List[Any]]:
        if not criteria and not group_conditions:
            return "", []
        
        parts: List[str] = []
        params: List[Any] = []
        
        if criteria:
            for item in criteria:
                field = self._validate_field(item["field"])
                op = item.get("op", "=").upper()
                
                if op not in ALLOWED_OPS:
                    raise ValueError(f"operator not allowed: {op!r}")
                
                value = item.get("value")
                processed_values, placeholder = self._process_value(value, op)
                
                if op in ("IS NULL", "IS NOT NULL"):
                    parts.append(f'"{field}" {op}')
                elif op in ("IN", "NOT IN"):
                    parts.append(f'"{field}" {op} {placeholder}')
                    params.extend(processed_values)
                elif op == "BETWEEN":
                    parts.append(f'"{field}" {op} {placeholder}')
                    params.extend(processed_values)
                else:
                    parts.append(f'"{field}" {op} {placeholder}')
                    params.extend(processed_values)
        
        if group_conditions:
            for group in group_conditions:
                group_parts = []
                for item in group:
                    field = self._validate_field(item["field"])
                    op = item.get("op", "=").upper()
                    
                    if op not in ALLOWED_OPS:
                        raise ValueError(f"operator not allowed: {op!r}")
                    
                    value = item.get("value")
                    processed_values, placeholder = self._process_value(value, op)
                    
                    if op in ("IS NULL", "IS NOT NULL"):
                        group_parts.append(f'"{field}" {op}')
                    elif op in ("IN", "NOT IN"):
                        group_parts.append(f'"{field}" {op} {placeholder}')
                        params.extend(processed_values)
                    elif op == "BETWEEN":
                        group_parts.append(f'"{field}" {op} {placeholder}')
                        params.extend(processed_values)
                    else:
                        group_parts.append(f'"{field}" {op} {placeholder}')
                        params.extend(processed_values)
                
                if group_parts:
                    parts.append(f"({' OR '.join(group_parts)})")
        
        joiner = " AND " if match == "all" else " OR "
        where_sql = joiner.join(parts)
        return where_sql, params
    
    def build_query(
        self,
        table: str,
        criteria: List[Dict[str, Any]] = None,
        select_fields: Optional[List[str]] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        group_by: Optional[List[str]] = None,
        having: Optional[List[Dict[str, Any]]] = None,
        joins: Optional[List[Dict[str, str]]] = None,
        match: Literal["all", "any"] = "all",
        group_conditions: Optional[List[List[Dict[str, Any]]]] = None
    ) -> Tuple[str, List[Any]]:
        t = self._validate_table(table)
        
        if select_fields:
            fields = ", ".join([f'"{self._validate_field(f)}"' for f in select_fields])
        else:
            fields = "*"
        
        sql = f'SELECT {fields} FROM "{t}"'
        
        if joins:
            for join in joins:
                join_type = join.get("type", "INNER").upper()
                if join_type not in ("INNER", "LEFT", "RIGHT", "FULL"):
                    raise ValueError(f"invalid join type: {join_type}")
                join_table = self._validate_table(join["table"])
                on_field1 = self._validate_field(join["on"][0])
                on_field2 = self._validate_field(join["on"][1])
                sql += f' {join_type} JOIN "{join_table}" ON "{on_field1}" = "{on_field2}"'
        
        params = []
        if criteria or group_conditions:
            where_sql, where_params = self.build_where(criteria or [], match, group_conditions)
            if where_sql:
                sql += f" WHERE {where_sql}"
                params.extend(where_params)
        
        if group_by:
            group_fields = ", ".join([f'"{self._validate_field(f)}"' for f in group_by])
            sql += f" GROUP BY {group_fields}"
        
        if having:
            having_sql, having_params = self.build_where(having, match="all")
            if having_sql:
                sql += f" HAVING {having_sql}"
                params.extend(having_params)
        
        if order_by:
            order_parts = []
            for order in order_by:
                field = self._validate_field(order["field"])
                direction = order.get("direction", "ASC").upper()
                if direction not in ("ASC", "DESC"):
                    raise ValueError(f"invalid order direction: {direction}")
                order_parts.append(f'"{field}" {direction}')
            sql += f" ORDER BY {', '.join(order_parts)}"
        
        if limit is not None:
            if not isinstance(limit, int) or limit < 0:
                raise ValueError("limit must be non-negative integer")
            sql += f" LIMIT {limit}"
        
        if offset is not None:
            if not isinstance(offset, int) or offset < 0:
                raise ValueError("offset must be non-negative integer")
            sql += f" OFFSET {offset}"
        
        return sql, params


def search(
    criteria: List[Dict[str, Any]],
    conn: Optional[sqlite3.Connection] = None,
    table: str = "users",
    allowed_fields: Optional[Sequence[str]] = None,
    select_fields: Optional[List[str]] = None,
    order_by: Optional[List[Dict[str, str]]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    group_by: Optional[List[str]] = None,
    having: Optional[List[Dict[str, Any]]] = None,
    joins: Optional[List[Dict[str, str]]] = None,
    match: Literal["all", "any"] = "all",
    group_conditions: Optional[List[List[Dict[str, Any]]]] = None,
    return_sql: bool = False
) -> Union[List[sqlite3.Row], Tuple[str, List[Any]]]:
    builder = QueryBuilder(allowed_fields)
    sql, params = builder.build_query(
        table=table,
        criteria=criteria,
        select_fields=select_fields,
        order_by=order_by,
        limit=limit,
        offset=offset,
        group_by=group_by,
        having=having,
        joins=joins,
        match=match,
        group_conditions=group_conditions
    )
    
    if return_sql:
        return sql, params
    
    if conn is None:
        raise ValueError("connection required when return_sql=False")
    
    cur = conn.execute(sql, params)
    return cur.fetchall()


def demo():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    conn.execute('''
        CREATE TABLE "users" (
            "id" INTEGER PRIMARY KEY,
            "name" TEXT,
            "age" INTEGER,
            "city" TEXT,
            "email" TEXT,
            "salary" DECIMAL,
            "department" TEXT,
            "joined_date" DATE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE "orders" (
            "id" INTEGER PRIMARY KEY,
            "user_id" INTEGER,
            "product" TEXT,
            "amount" DECIMAL,
            "order_date" DATE
        )
    ''')
    
    users_data = [
        ("Alice", 25, "NYC", "alice@example.com", 75000, "Engineering", "2020-01-15"),
        ("Bob", 17, "LA", "bob@example.com", 45000, "Sales", "2021-03-22"),
        ("Charlie", 30, "NYC", "charlie@example.com", 85000, "Engineering", "2019-07-01"),
        ("Diana", 22, "Boston", "diana@example.com", 60000, "Marketing", "2022-02-10"),
        ("Eve", 28, "NYC", "eve@example.com", 70000, "Sales", "2020-11-30"),
        ("Frank", 35, "LA", "frank@example.com", 95000, "Engineering", "2018-05-15"),
        ("Grace", 26, "Boston", "grace@example.com", 65000, "Marketing", "2021-09-01"),
    ]
    
    conn.executemany(
        'INSERT INTO "users" ("name", "age", "city", "email", "salary", "department", "joined_date") VALUES (?, ?, ?, ?, ?, ?, ?)',
        users_data
    )
    
    orders_data = [
        (1, "Laptop", 1200, "2023-01-15"),
        (1, "Mouse", 25, "2023-01-20"),
        (2, "Keyboard", 80, "2023-02-01"),
        (3, "Monitor", 450, "2023-02-15"),
        (3, "Laptop", 1500, "2023-03-01"),
        (4, "Mouse", 30, "2023-03-10"),
        (5, "Keyboard", 100, "2023-03-15"),
    ]
    
    conn.executemany(
        'INSERT INTO "orders" ("user_id", "product", "amount", "order_date") VALUES (?, ?, ?, ?)',
        orders_data
    )
    
    conn.commit()
    
    print("Example 1: Basic search with multiple conditions (AND)")
    q1 = [
        {"field": "age", "op": ">", "value": 18},
        {"field": "city", "op": "=", "value": "NYC"}
    ]
    rows = search(q1, conn, table="users")
    for r in rows:
        print(dict(r))
    print()
    
    print("Example 2: Search with LIKE operator")
    q2 = [
        {"field": "email", "op": "LIKE", "value": "%@example.com"},
        {"field": "department", "op": "=", "value": "Engineering"}
    ]
    rows = search(q2, conn, table="users")
    for r in rows:
        print(dict(r))
    print()
    
    print("Example 3: Search with IN operator")
    q3 = [
        {"field": "city", "op": "IN", "value": ["NYC", "Boston"]},
        {"field": "age", "op": ">=", "value": 25}
    ]
    rows = search(q3, conn, table="users")
    for r in rows:
        print(dict(r))
    print()
    
    print("Example 4: Search with BETWEEN operator")
    q4 = [
        {"field": "salary", "op": "BETWEEN", "value": [60000, 80000]}
    ]
    rows = search(q4, conn, table="users", order_by=[{"field": "salary", "direction": "DESC"}])
    for r in rows:
        print(dict(r))
    print()
    
    print("Example 5: Search with OR conditions")
    q5 = [
        {"field": "department", "op": "=", "value": "Sales"},
        {"field": "department", "op": "=", "value": "Marketing"}
    ]
    rows = search(q5, conn, table="users", match="any")
    for r in rows:
        print(dict(r))
    print()
    
    print("Example 6: Complex search with grouped conditions")
    rows = search(
        criteria=[{"field": "age", "op": ">", "value": 20}],
        group_conditions=[
            [
                {"field": "city", "op": "=", "value": "NYC"},
                {"field": "city", "op": "=", "value": "LA"}
            ]
        ],
        conn=conn,
        table="users"
    )
    for r in rows:
        print(dict(r))
    print()
    
    print("Example 7: Search with JOIN")
    rows = search(
        criteria=[{"field": "users.age", "op": ">", "value": 25}],
        conn=conn,
        table="users",
        joins=[{
            "type": "LEFT",
            "table": "orders",
            "on": ["users.id", "orders.user_id"]
        }],
        select_fields=["users.name", "users.age", "orders.product", "orders.amount"],
        allowed_fields=["users.age", "users.name", "orders.product", "orders.amount", "users.id", "orders.user_id"]
    )
    for r in rows:
        print(dict(r))
    print()
    
    print("Example 8: Search with GROUP BY and HAVING")
    builder = QueryBuilder(allowed_fields=["user_id", "total_amount"])
    sql = '''
        SELECT user_id, SUM(amount) as total_amount 
        FROM orders 
        GROUP BY user_id 
        HAVING SUM(amount) > ?
    '''
    cur = conn.execute(sql, [500])
    rows = cur.fetchall()
    for r in rows:
        print(dict(r))
    print()
    
    print("Example 9: Search with IS NULL / IS NOT NULL")
    conn.execute('INSERT INTO "users" ("name", "age", "city") VALUES (?, ?, ?)', ("TestUser", None, "TestCity"))
    q9 = [{"field": "email", "op": "IS NULL"}]
    rows = search(q9, conn, table="users")
    for r in rows:
        print(dict(r))
    print()
    
    print("Example 10: Get SQL query without executing")
    q10 = [
        {"field": "age", "op": ">", "value": 25},
        {"field": "department", "op": "NOT IN", "value": ["Sales", "Marketing"]}
    ]
    sql, params = search(
        q10,
        table="users",
        select_fields=["name", "age", "department"],
        order_by=[{"field": "age", "direction": "ASC"}],
        limit=5,
        return_sql=True,
        allowed_fields=["age", "department", "name"]
    )
    print(f"SQL: {sql}")
    print(f"Parameters: {params}")


if __name__ == "__main__":
    demo()
