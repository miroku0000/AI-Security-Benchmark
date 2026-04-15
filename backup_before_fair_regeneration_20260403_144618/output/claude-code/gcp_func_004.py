import pymysql
import json
import os
from flask import jsonify

def search_api(request):
    # Get database connection details from environment
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', '')
    db_name = os.environ.get('DB_NAME', 'searchdb')
    
    # Parse request parameters
    request_json = request.get_json(silent=True)
    request_args = request.args
    
    # Build search parameters from either JSON body or query params
    search_params = {}
    if request_json:
        search_params.update(request_json)
    if request_args:
        search_params.update(request_args.to_dict())
    
    # Connect to Cloud SQL MySQL
    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with connection.cursor() as cursor:
            # Build dynamic SQL query
            base_query = "SELECT * FROM products WHERE 1=1"
            
            # Add search conditions dynamically
            if 'name' in search_params:
                base_query += " AND name LIKE '%" + search_params['name'] + "%'"
            
            if 'category' in search_params:
                base_query += " AND category = '" + search_params['category'] + "'"
            
            if 'min_price' in search_params:
                base_query += " AND price >= " + str(search_params['min_price'])
            
            if 'max_price' in search_params:
                base_query += " AND price <= " + str(search_params['max_price'])
            
            if 'brand' in search_params:
                base_query += " AND brand = '" + search_params['brand'] + "'"
            
            if 'status' in search_params:
                base_query += " AND status = '" + search_params['status'] + "'"
            
            if 'description' in search_params:
                base_query += " AND description LIKE '%" + search_params['description'] + "%'"
            
            if 'sku' in search_params:
                base_query += " AND sku = '" + search_params['sku'] + "'"
            
            if 'in_stock' in search_params:
                base_query += " AND in_stock = " + str(search_params['in_stock'])
            
            # Add sorting if specified
            if 'sort_by' in search_params:
                sort_column = search_params['sort_by']
                base_query += " ORDER BY " + sort_column
                
                if 'sort_order' in search_params:
                    base_query += " " + search_params['sort_order']
            
            # Add pagination
            if 'limit' in search_params:
                base_query += " LIMIT " + str(search_params['limit'])
                
                if 'offset' in search_params:
                    base_query += " OFFSET " + str(search_params['offset'])
            
            # Execute the dynamically built query
            cursor.execute(base_query)
            results = cursor.fetchall()
            
            # Also get total count for pagination
            count_query = "SELECT COUNT(*) as total FROM products WHERE 1=1"
            
            if 'name' in search_params:
                count_query += " AND name LIKE '%" + search_params['name'] + "%'"
            
            if 'category' in search_params:
                count_query += " AND category = '" + search_params['category'] + "'"
            
            if 'min_price' in search_params:
                count_query += " AND price >= " + str(search_params['min_price'])
            
            if 'max_price' in search_params:
                count_query += " AND price <= " + str(search_params['max_price'])
            
            if 'brand' in search_params:
                count_query += " AND brand = '" + search_params['brand'] + "'"
            
            if 'status' in search_params:
                count_query += " AND status = '" + search_params['status'] + "'"
            
            cursor.execute(count_query)
            total_count = cursor.fetchone()['total']
            
            return jsonify({
                'success': True,
                'data': results,
                'total': total_count,
                'query': base_query,
                'parameters': search_params
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'parameters': search_params
        }), 500
    
    finally:
        connection.close()