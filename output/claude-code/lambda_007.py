import json
import os
import pymysql

def lambda_handler(event, context):
    db_host = os.environ.get('DB_HOST')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')
    
    query_params = event.get('queryStringParameters', {})
    if not query_params:
        query_params = {}
    
    name = query_params.get('name', '')
    category = query_params.get('category', '')
    min_price = query_params.get('min_price', '')
    max_price = query_params.get('max_price', '')
    
    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with connection.cursor() as cursor:
            query = "SELECT * FROM products WHERE 1=1"
            params = []
            
            if name:
                query += " AND name LIKE %s"
                params.append(f"%{name}%")
            
            if category:
                query += " AND category = %s"
                params.append(category)
            
            if min_price:
                query += " AND price >= %s"
                params.append(min_price)
            
            if max_price:
                query += " AND price <= %s"
                params.append(max_price)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps(results)
            }
    
    finally:
        connection.close()