import json
import psycopg2

def lambda_handler(event, context):
    conn = psycopg2.connect('postgresql://admin:password@internal-db.us-east-1.rds.amazonaws.com:5432/production')
    cur = conn.cursor()
    
    query = event.get('query', 'SELECT * FROM users LIMIT 10')
    cur.execute(query)
    
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    
    results = []
    for row in rows:
        results.append(dict(zip(columns, row)))
    
    cur.close()
    conn.close()
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }