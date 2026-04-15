import json
import base64
import urllib.request
import urllib.error
from urllib.parse import urlparse

def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']
    
    # Check for X-Enrich-URL header
    enrich_url_header = headers.get('x-enrich-url', [])
    if enrich_url_header:
        enrich_url = enrich_url_header[0]['value']
        
        try:
            # Parse and validate URL
            parsed_url = urlparse(enrich_url)
            
            # Create request with timeout
            req = urllib.request.Request(enrich_url)
            req.add_header('User-Agent', 'Lambda-Edge-Enrichment/1.0')
            
            # Fetch data from the URL
            with urllib.request.urlopen(req, timeout=3) as response:
                data = response.read()
                
                # Add enrichment data as custom header (base64 encoded to handle special chars)
                encoded_data = base64.b64encode(data).decode('utf-8')
                
                # CloudFront has header size limits, truncate if needed
                if len(encoded_data) > 8192:
                    encoded_data = encoded_data[:8192]
                
                headers['x-enrichment-data'] = [{
                    'key': 'X-Enrichment-Data',
                    'value': encoded_data
                }]
                
                # Add status header
                headers['x-enrichment-status'] = [{
                    'key': 'X-Enrichment-Status',
                    'value': 'success'
                }]
                
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
            # Add error status but continue request
            headers['x-enrichment-status'] = [{
                'key': 'X-Enrichment-Status',
                'value': 'failed'
            }]
            headers['x-enrichment-error'] = [{
                'key': 'X-Enrichment-Error',
                'value': str(e)[:256]
            }]
        except Exception as e:
            # Catch all other exceptions
            headers['x-enrichment-status'] = [{
                'key': 'X-Enrichment-Status',
                'value': 'error'
            }]
    
    # Process multiple enrichment URLs if provided
    for i in range(2, 6):  # Support up to 5 enrichment URLs
        header_name = f'x-enrich-url-{i}'
        enrich_url_header = headers.get(header_name, [])
        
        if enrich_url_header:
            enrich_url = enrich_url_header[0]['value']
            
            try:
                parsed_url = urlparse(enrich_url)
                
                req = urllib.request.Request(enrich_url)
                req.add_header('User-Agent', 'Lambda-Edge-Enrichment/1.0')
                
                with urllib.request.urlopen(req, timeout=2) as response:
                    data = response.read()
                    encoded_data = base64.b64encode(data).decode('utf-8')
                    
                    if len(encoded_data) > 4096:
                        encoded_data = encoded_data[:4096]
                    
                    headers[f'x-enrichment-data-{i}'] = [{
                        'key': f'X-Enrichment-Data-{i}',
                        'value': encoded_data
                    }]
                    
            except Exception:
                # Silently skip failed secondary enrichments
                pass
    
    # Forward modified request to origin
    return request