import sqlite3
import re
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal
import json


class QueryBuilder:
    ALLOWED_OPERATORS = {
        '=': '=',
        '!=': '!=',
        '<>': '<>',
        '>': '>',
        '>=': '>=',
        '<': '<',
        '<=': '<=',
        'LIKE': 'LIKE',
        'NOT LIKE': 'NOT LIKE',
        'IN': 'IN',
        'NOT IN': 'NOT IN',
        'BETWEEN': 'BETWEEN',
        'IS NULL': 'IS NULL',
        'IS NOT NULL': 'IS NOT NULL'
    }
    
    def __init__(self, table_name: str, allowed_fields: Optional[List[str]] = None):
        self.table_name = self._sanitize_identifier(table_name)
        self.allowed_fields = allowed_fields
        self.params = []
        self.param_counter = 0
    
    def _sanitize_identifier(self, identifier: str) -> str:
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise ValueError(f"Invalid identifier: {identifier}")
        return identifier
    
    def _validate_field(self, field: str) -> str:
        field = self._sanitize_identifier(field)
        if self.allowed_fields and field not in self.allowed_fields:
            raise ValueError(f"Field '{field}' is not allowed")
        return field
    
    def _validate_operator(self, operator: str) -> str:
        op = operator.upper()
        if op not in self.ALLOWED_OPERATORS:
            raise ValueError(f"Invalid operator: {operator}")
        return self.ALLOWED_OPERATORS[op]
    
    def _process_value(self, value: Any, operator: str) -> tuple:
        op = operator.upper()
        
        if op in ['IS NULL', 'IS NOT NULL']:
            return '', []
        
        if op in ['IN', 'NOT IN']:
            if not isinstance(value, (list, tuple)):
                value = [value]
            placeholders = ', '.join(['?' for _ in value])
            return f'({placeholders})', list(value)
        
        if op == 'BETWEEN':
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError("BETWEEN requires a list/tuple of 2 values")
            return '? AND ?', list(value)
        
        return '?', [value]
    
    def build_where_clause(self, conditions: List[Dict[str, Any]], logic: str = 'AND') -> str:
        if not conditions:
            return '', []
        
        logic = logic.upper()
        if logic not in ['AND', 'OR']:
            raise ValueError("Logic must be 'AND' or 'OR'")
        
        where_parts = []
        params = []
        
        for condition in conditions:
            if 'field' not in condition:
                raise ValueError("Each condition must have a 'field'")
            
            field = self._validate_field(condition['field'])
            operator = self._validate_operator(condition.get('op', '='))
            
            if operator in ['IS NULL', 'IS NOT NULL']:
                where_parts.append(f"{field} {operator}")
            else:
                if 'value' not in condition:
                    raise ValueError(f"Condition for field '{field}' requires a 'value'")
                
                value_clause, value_params = self._process_value(condition['value'], operator)
                
                if operator == 'BETWEEN':
                    where_parts.append(f"{field} BETWEEN {value_clause}")
                else:
                    where_parts.append(f"{field} {operator} {value_clause}")
                
                params.extend(value_params)
        
        where_clause = f" {logic} ".join(where_parts)
        return f"WHERE {where_clause}", params


class AdvancedDatabaseSearch:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
    
    def __enter__(self):
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
    
    def search(
        self,
        table: str,
        conditions: List[Dict[str, Any]],
        fields: Optional[List[str]] = None,
        logic: str = 'AND',
        order_by: Optional[str] = None,
        order_direction: str = 'ASC',
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        group_by: Optional[List[str]] = None,
        having: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        query_builder = QueryBuilder(table)
        
        if fields:
            field_list = ', '.join([query_builder._sanitize_identifier(f) for f in fields])
        else:
            field_list = '*'
        
        base_query = f"SELECT {field_list} FROM {table}"
        
        where_clause, params = query_builder.build_where_clause(conditions, logic)
        
        query_parts = [base_query]
        if where_clause:
            query_parts.append(where_clause)
        
        if group_by:
            group_fields = ', '.join([query_builder._sanitize_identifier(f) for f in group_by])
            query_parts.append(f"GROUP BY {group_fields}")
            
            if having:
                having_builder = QueryBuilder(table)
                having_clause, having_params = having_builder.build_where_clause(having, 'AND')
                query_parts.append(having_clause.replace('WHERE', 'HAVING'))
                params.extend(having_params)
        
        if order_by:
            order_field = query_builder._sanitize_identifier(order_by)
            if order_direction.upper() not in ['ASC', 'DESC']:
                raise ValueError("Order direction must be 'ASC' or 'DESC'")
            query_parts.append(f"ORDER BY {order_field} {order_direction.upper()}")
        
        if limit:
            if not isinstance(limit, int) or limit < 0:
                raise ValueError("Limit must be a non-negative integer")
            query_parts.append(f"LIMIT {limit}")
            
            if offset:
                if not isinstance(offset, int) or offset < 0:
                    raise ValueError("Offset must be a non-negative integer")
                query_parts.append(f"OFFSET {offset}")
        
        query = ' '.join(query_parts)
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def search_multiple_tables(
        self,
        searches: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        
        results = {}
        for search_config in searches:
            table = search_config.get('table')
            if not table:
                continue
            
            conditions = search_config.get('conditions', [])
            
            result = self.search(
                table=table,
                conditions=conditions,
                fields=search_config.get('fields'),
                logic=search_config.get('logic', 'AND'),
                order_by=search_config.get('order_by'),
                order_direction=search_config.get('order_direction', 'ASC'),
                limit=search_config.get('limit'),
                offset=search_config.get('offset'),
                group_by=search_config.get('group_by'),
                having=search_config.get('having')
            )
            
            results[table] = result
        
        return results
    
    def search_with_joins(
        self,
        base_table: str,
        joins: List[Dict[str, str]],
        conditions: List[Dict[str, Any]],
        fields: Optional[List[str]] = None,
        logic: str = 'AND'
    ) -> List[Dict[str, Any]]:
        
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        query_builder = QueryBuilder(base_table)
        
        if fields:
            field_list = ', '.join(fields)
        else:
            field_list = '*'
        
        query_parts = [f"SELECT {field_list} FROM {base_table}"]
        
        for join in joins:
            join_type = join.get('type', 'INNER').upper()
            if join_type not in ['INNER', 'LEFT', 'RIGHT', 'FULL OUTER']:
                raise ValueError(f"Invalid join type: {join_type}")
            
            table = query_builder._sanitize_identifier(join['table'])
            on_clause = join.get('on', '')
            
            query_parts.append(f"{join_type} JOIN {table} ON {on_clause}")
        
        where_clause, params = query_builder.build_where_clause(conditions, logic)
        if where_clause:
            query_parts.append(where_clause)
        
        query = ' '.join(query_parts)
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def search(conditions: List[Dict[str, Any]], table: str = 'users', db_path: str = 'database.db', **kwargs):
    with AdvancedDatabaseSearch(db_path) as searcher:
        return searcher.search(table, conditions, **kwargs)


def create_sample_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            city TEXT,
            email TEXT,
            created_at DATE,
            is_active BOOLEAN,
            salary DECIMAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            product TEXT,
            quantity INTEGER,
            price DECIMAL,
            order_date DATE,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price DECIMAL,
            stock INTEGER,
            description TEXT
        )
    ''')
    
    sample_users = [
        (1, 'John Doe', 25, 'NYC', 'john@example.com', '2023-01-15', 1, 65000),
        (2, 'Jane Smith', 30, 'LA', 'jane@example.com', '2023-02-20', 1, 75000),
        (3, 'Bob Johnson', 22, 'NYC', 'bob@example.com', '2023-03-10', 1, 55000),
        (4, 'Alice Brown', 35, 'Chicago', 'alice@example.com', '2023-04-05', 0, 80000),
        (5, 'Charlie Wilson', 28, 'NYC', 'charlie@example.com', '2023-05-12', 1, 70000),
        (6, 'Emma Davis', 19, 'Boston', 'emma@example.com', '2023-06-18', 1, 45000),
        (7, 'Frank Miller', 45, 'NYC', 'frank@example.com', '2023-07-22', 1, 95000),
        (8, 'Grace Lee', 33, 'Seattle', 'grace@example.com', '2023-08-30', 1, 85000),
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)', sample_users)
    
    sample_orders = [
        (1, 1, 'Laptop', 1, 1200.00, '2023-10-01', 'delivered'),
        (2, 2, 'Phone', 2, 800.00, '2023-10-02', 'delivered'),
        (3, 1, 'Tablet', 1, 600.00, '2023-10-03', 'pending'),
        (4, 3, 'Laptop', 1, 1200.00, '2023-10-04', 'delivered'),
        (5, 4, 'Phone', 1, 800.00, '2023-10-05', 'cancelled'),
        (6, 5, 'Headphones', 3, 150.00, '2023-10-06', 'delivered'),
        (7, 2, 'Keyboard', 2, 100.00, '2023-10-07', 'pending'),
        (8, 6, 'Mouse', 1, 50.00, '2023-10-08', 'delivered'),
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)', sample_orders)
    
    sample_products = [
        (1, 'Laptop Pro', 'Electronics', 1200.00, 50, 'High-performance laptop'),
        (2, 'Smartphone X', 'Electronics', 800.00, 100, 'Latest smartphone model'),
        (3, 'Tablet Plus', 'Electronics', 600.00, 75, 'Versatile tablet device'),
        (4, 'Wireless Headphones', 'Audio', 150.00, 200, 'Premium sound quality'),
        (5, 'Mechanical Keyboard', 'Accessories', 100.00, 150, 'Gaming keyboard'),
        (6, 'Optical Mouse', 'Accessories', 50.00, 300, 'Precision mouse'),
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?, ?, ?)', sample_products)
    
    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_sample_database()
    
    print("Example 1: Basic search with multiple conditions")
    results = search([
        {'field': 'age', 'op': '>', 'value': 18},
        {'field': 'city', 'op': '=', 'value': 'NYC'}
    ])
    print(json.dumps(results, indent=2))
    print()
    
    print("Example 2: Search with LIKE operator")
    results = search([
        {'field': 'email', 'op': 'LIKE', 'value': '%@example.com'}
    ])
    print(json.dumps(results, indent=2))
    print()
    
    print("Example 3: Search with IN operator")
    results = search([
        {'field': 'city', 'op': 'IN', 'value': ['NYC', 'LA', 'Chicago']}
    ])
    print(json.dumps(results, indent=2))
    print()
    
    print("Example 4: Search with BETWEEN operator")
    results = search([
        {'field': 'age', 'op': 'BETWEEN', 'value': [25, 35]}
    ], order_by='age', limit=5)
    print(json.dumps(results, indent=2))
    print()
    
    print("Example 5: Complex search with OR logic")
    results = search([
        {'field': 'age', 'op': '<', 'value': 25},
        {'field': 'salary', 'op': '>', 'value': 80000}
    ], logic='OR', fields=['name', 'age', 'salary', 'city'])
    print(json.dumps(results, indent=2))
    print()
    
    print("Example 6: Search orders table")
    results = search([
        {'field': 'status', 'op': '=', 'value': 'delivered'},
        {'field': 'price', 'op': '>=', 'value': 500}
    ], table='orders')
    print(json.dumps(results, indent=2))
    print()
    
    print("Example 7: Advanced search with database context")
    with AdvancedDatabaseSearch('database.db') as searcher:
        results = searcher.search_with_joins(
            base_table='orders',
            joins=[
                {'table': 'users', 'on': 'orders.user_id = users.id'}
            ],
            conditions=[
                {'field': 'orders.status', 'op': '=', 'value': 'delivered'},
                {'field': 'users.city', 'op': '=', 'value': 'NYC'}
            ],
            fields=['orders.id', 'users.name', 'orders.product', 'orders.price', 'users.city']
        )
        print(json.dumps(results, indent=2))
        print()
        
        multi_results = searcher.search_multiple_tables([
            {
                'table': 'users',
                'conditions': [{'field': 'is_active', 'op': '=', 'value': 1}],
                'fields': ['name', 'city'],
                'limit': 3
            },
            {
                'table': 'products',
                'conditions': [{'field': 'stock', 'op': '>', 'value': 100}],
                'fields': ['name', 'price', 'stock']
            }
        ])
        print("Multiple table search results:")
        print(json.dumps(multi_results, indent=2))