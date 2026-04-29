import json
import urllib3
from datetime import datetime

http = urllib3.PoolManager()

def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']
    
    enriched_data = {}
    
    if 'x-enrich-url' in headers:
        enrich_urls = headers['x-enrich-url']
        if isinstance(enrich_urls, list) and len(enrich_urls) > 0:
            url = enrich_urls[0]['value']
            enriched_data = fetch_enrichment_data(url)
    
    enriched_data['timestamp'] = datetime.utcnow().isoformat()
    enriched_data['client_ip'] = request['clientIp']
    enriched_data['request_uri'] = request['uri']
    enriched_data['request_method'] = request['method']
    enriched_data['domain'] = headers.get('host', [{'value': 'unknown'}])[0]['value']
    
    request['headers']['x-enriched-data'] = [
        {'key': 'X-Enriched-Data', 'value': json.dumps(enriched_data)}
    ]
    
    return request


def fetch_enrichment_data(url):
    try:
        response = http.request('GET', url, timeout=5.0, retries=urllib3.Retry(connect=2))
        
        if response.status == 200:
            try:
                data = json.loads(response.data.decode('utf-8'))
                return {
                    'enrichment_status': 'success',
                    'data': data,
                    'source_url': url,
                    'status_code': response.status
                }
            except json.JSONDecodeError:
                return {
                    'enrichment_status': 'success',
                    'data': response.data.decode('utf-8'),
                    'source_url': url,
                    'status_code': response.status,
                    'is_json': False
                }
        else:
            return {
                'enrichment_status': 'error',
                'source_url': url,
                'status_code': response.status,
                'error': 'Non-200 response'
            }
    
    except Exception as e:
        return {
            'enrichment_status': 'error',
            'source_url': url,
            'error': str(e),
            'error_type': type(e).__name__
        }


def lambda_handler_with_multiple_urls(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']
    
    enriched_data = {}
    enrichment_results = []
    
    if 'x-enrich-urls' in headers:
        urls = headers['x-enrich-urls'][0]['value'].split(',')
        for url in urls:
            url = url.strip()
            if url:
                result = fetch_enrichment_data(url)
                enrichment_results.append(result)
    
    enriched_data['timestamp'] = datetime.utcnow().isoformat()
    enriched_data['client_ip'] = request['clientIp']
    enriched_data['request_uri'] = request['uri']
    enriched_data['request_method'] = request['method']
    enriched_data['domain'] = headers.get('host', [{'value': 'unknown'}])[0]['value']
    enriched_data['enrichment_results'] = enrichment_results
    enriched_data['enrichment_count'] = len(enrichment_results)
    
    request['headers']['x-enriched-data'] = [
        {'key': 'X-Enriched-Data', 'value': json.dumps(enriched_data)}
    ]
    
    return request


def lambda_handler_with_context_headers(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']
    
    enriched_context = {
        'request_id': context.request_id if hasattr(context, 'request_id') else 'unknown',
        'function_version': context.function_version if hasattr(context, 'function_version') else 'unknown',
        'function_name': context.function_name if hasattr(context, 'function_name') else 'unknown',
        'memory_limit_mb': context.memory_limit_in_mb if hasattr(context, 'memory_limit_in_mb') else 'unknown',
        'timestamp': datetime.utcnow().isoformat(),
        'client_ip': request['clientIp'],
        'request_uri': request['uri'],
        'cloudfront_id': headers.get('cloudfront-viewer-country', [{'value': 'unknown'}])[0]['value']
    }
    
    if 'x-enrich-url' in headers:
        enrich_urls = headers['x-enrich-url']
        if isinstance(enrich_urls, list) and len(enrich_urls) > 0:
            url = enrich_urls[0]['value']
            enriched_context['external_data'] = fetch_enrichment_data(url)
    
    for header_name, header_value in headers.items():
        if header_name.lower().startswith('x-'):
            if isinstance(header_value, list) and len(header_value) > 0:
                enriched_context[f'header_{header_name}'] = header_value[0].get('value', '')
    
    request['headers']['x-enriched-context'] = [
        {'key': 'X-Enriched-Context', 'value': json.dumps(enriched_context)}
    ]
    
    return request


def lambda_handler_cached(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']
    
    cache_key = f"enrichment_{request.get('uri', 'default')}"
    
    enriched_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'client_ip': request['clientIp'],
        'request_uri': request['uri'],
        'cache_key': cache_key
    }
    
    if 'x-enrich-url' in headers:
        enrich_urls = headers['x-enrich-url']
        if isinstance(enrich_urls, list) and len(enrich_urls) > 0:
            url = enrich_urls[0]['value']
            result = fetch_enrichment_data(url)
            enriched_data['external_data'] = result
            
            if result.get('enrichment_status') == 'success':
                request['headers']['cache-control'] = [
                    {'key': 'Cache-Control', 'value': 'max-age=3600'}
                ]
            else:
                request['headers']['cache-control'] = [
                    {'key': 'Cache-Control', 'value': 'max-age=60'}
                ]
    
    request['headers']['x-enriched-data'] = [
        {'key': 'X-Enriched-Data', 'value': json.dumps(enriched_data)}
    ]
    
    return request