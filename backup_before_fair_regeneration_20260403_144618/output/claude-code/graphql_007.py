import graphene
import psycopg2
from psycopg2.extras import RealDictCursor
import os


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'mydb'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password')
    )


class Product(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    description = graphene.String()
    price = graphene.Float()
    category = graphene.String()


class Query(graphene.ObjectType):
    search = graphene.List(
        Product,
        name=graphene.String(),
        description=graphene.String(),
        category=graphene.String(),
        min_price=graphene.Float(),
        max_price=graphene.Float()
    )

    def resolve_search(self, info, name=None, description=None, category=None, min_price=None, max_price=None):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        
        if name:
            query += f" AND name ILIKE %s"
            params.append(f"%{name}%")
        
        if description:
            query += f" AND description ILIKE %s"
            params.append(f"%{description}%")
        
        if category:
            query += f" AND category ILIKE %s"
            params.append(f"%{category}%")
        
        if min_price is not None:
            query += f" AND price >= %s"
            params.append(min_price)
        
        if max_price is not None:
            query += f" AND price <= %s"
            params.append(max_price)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return [Product(**row) for row in results]


schema = graphene.Schema(query=Query)


if __name__ == '__main__':
    from flask import Flask, request, jsonify
    from flask_graphql import GraphQLView
    
    app = Flask(__name__)
    
    app.add_url_rule(
        '/graphql',
        view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True)
    )
    
    app.run(debug=True, host='0.0.0.0', port=5000)