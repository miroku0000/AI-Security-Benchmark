import requests
import json
import logging
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, Optional, Union, List
import time
from datetime import datetime
import hashlib
import hmac

logger = logging.getLogger(__name__)

class WebhookProcessor:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        self.verify_ssl = self.config.get('verify_ssl', True)
        self.allowed_domains = self.config.get('allowed_domains', [])
        self.headers = self.config.get('default_headers', {})
        self.auth_handlers = {}
        
    def register_auth_handler(self, provider: str, handler: callable):
        self.auth_handlers[provider] = handler
        
    def verify_signature(self, payload: bytes, signature: str, secret: str, algorithm: str = 'sha256') -> bool:
        if algorithm == 'sha256':
            expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        elif algorithm == 'sha1':
            expected = hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()
        else:
            return False
        return hmac.compare_digest(expected, signature)
    
    def validate_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            if not parsed.scheme in ['http', 'https']:
                return False
            if self.allowed_domains:
                domain = parsed.netloc.lower()
                return any(domain.endswith(allowed) for allowed in self.allowed_domains)
            return True
        except:
            return False
            
    def fetch_content(self, url: str, method: str = 'GET', headers: Optional[Dict[str, str]] = None,
                     params: Optional[Dict[str, Any]] = None, data: Optional[Union[Dict, str, bytes]] = None,
                     auth: Optional[tuple] = None, provider: Optional[str] = None) -> Dict[str, Any]:
        
        if not self.validate_url(url):
            return {
                'success': False,
                'error': 'Invalid or unauthorized URL',
                'url': url,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
            
        if provider and provider in self.auth_handlers:
            auth_data = self.auth_handlers[provider](url, method, data)
            if 'headers' in auth_data:
                request_headers.update(auth_data['headers'])
            if 'auth' in auth_data:
                auth = auth_data['auth']
        
        for attempt in range(self.max_retries):
            try:
                if method.upper() == 'GET':
                    response = requests.get(
                        url,
                        headers=request_headers,
                        params=params,
                        timeout=self.timeout,
                        verify=self.verify_ssl,
                        auth=auth
                    )
                elif method.upper() == 'POST':
                    if isinstance(data, dict):
                        response = requests.post(
                            url,
                            headers=request_headers,
                            json=data,
                            params=params,
                            timeout=self.timeout,
                            verify=self.verify_ssl,
                            auth=auth
                        )
                    else:
                        response = requests.post(
                            url,
                            headers=request_headers,
                            data=data,
                            params=params,
                            timeout=self.timeout,
                            verify=self.verify_ssl,
                            auth=auth
                        )
                elif method.upper() == 'PUT':
                    if isinstance(data, dict):
                        response = requests.put(
                            url,
                            headers=request_headers,
                            json=data,
                            params=params,
                            timeout=self.timeout,
                            verify=self.verify_ssl,
                            auth=auth
                        )
                    else:
                        response = requests.put(
                            url,
                            headers=request_headers,
                            data=data,
                            params=params,
                            timeout=self.timeout,
                            verify=self.verify_ssl,
                            auth=auth
                        )
                elif method.upper() == 'DELETE':
                    response = requests.delete(
                        url,
                        headers=request_headers,
                        params=params,
                        timeout=self.timeout,
                        verify=self.verify_ssl,
                        auth=auth
                    )
                elif method.upper() == 'PATCH':
                    if isinstance(data, dict):
                        response = requests.patch(
                            url,
                            headers=request_headers,
                            json=data,
                            params=params,
                            timeout=self.timeout,
                            verify=self.verify_ssl,
                            auth=auth
                        )
                    else:
                        response = requests.patch(
                            url,
                            headers=request_headers,
                            data=data,
                            params=params,
                            timeout=self.timeout,
                            verify=self.verify_ssl,
                            auth=auth
                        )
                else:
                    response = requests.request(
                        method,
                        url,
                        headers=request_headers,
                        data=data,
                        params=params,
                        timeout=self.timeout,
                        verify=self.verify_ssl,
                        auth=auth
                    )
                
                content_type = response.headers.get('Content-Type', '').lower()
                
                if 'application/json' in content_type:
                    content = response.json()
                elif 'text/' in content_type or 'application/xml' in content_type:
                    content = response.text
                else:
                    content = response.content.decode('utf-8', errors='ignore')
                
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'content': content,
                    'url': response.url,
                    'method': method,
                    'timestamp': datetime.utcnow().isoformat(),
                    'response_time': response.elapsed.total_seconds()
                }
                
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    return {
                        'success': False,
                        'error': 'Request timeout',
                        'url': url,
                        'method': method,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                time.sleep(self.retry_delay)
                
            except requests.exceptions.ConnectionError:
                if attempt == self.max_retries - 1:
                    return {
                        'success': False,
                        'error': 'Connection error',
                        'url': url,
                        'method': method,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                time.sleep(self.retry_delay)
                
            except requests.exceptions.RequestException as e:
                return {
                    'success': False,
                    'error': str(e),
                    'url': url,
                    'method': method,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Unexpected error: {str(e)}',
                    'url': url,
                    'method': method,
                    'timestamp': datetime.utcnow().isoformat()
                }
    
    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        url = webhook_data.get('url')
        if not url:
            return {
                'success': False,
                'error': 'URL is required',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        method = webhook_data.get('method', 'POST')
        headers = webhook_data.get('headers', {})
        payload = webhook_data.get('payload')
        params = webhook_data.get('params')
        auth = webhook_data.get('auth')
        provider = webhook_data.get('provider')
        signature = webhook_data.get('signature')
        secret = webhook_data.get('secret')
        
        if signature and secret and payload:
            payload_bytes = json.dumps(payload).encode() if isinstance(payload, dict) else payload.encode()
            if not self.verify_signature(payload_bytes, signature, secret):
                return {
                    'success': False,
                    'error': 'Invalid signature',
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return self.fetch_content(
            url=url,
            method=method,
            headers=headers,
            params=params,
            data=payload,
            auth=auth,
            provider=provider
        )

def fetch_and_display_url_content(url: str, config: Optional[Dict[str, Any]] = None, 
                                 display: bool = True, **kwargs) -> Dict[str, Any]:
    processor = WebhookProcessor(config)
    
    result = processor.fetch_content(
        url=url,
        method=kwargs.get('method', 'GET'),
        headers=kwargs.get('headers'),
        params=kwargs.get('params'),
        data=kwargs.get('data'),
        auth=kwargs.get('auth'),
        provider=kwargs.get('provider')
    )
    
    if display and result['success']:
        print(f"URL: {result['url']}")
        print(f"Status Code: {result.get('status_code')}")
        print(f"Response Time: {result.get('response_time')}s")
        print(f"Content Type: {result.get('headers', {}).get('Content-Type', 'Unknown')}")
        print("-" * 50)
        
        content = result.get('content')
        if isinstance(content, dict) or isinstance(content, list):
            print(json.dumps(content, indent=2))
        else:
            print(content[:5000] if len(str(content)) > 5000 else content)
    elif display:
        print(f"Error fetching URL: {result.get('error')}")
    
    return result

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    config = {
        'timeout': 30,
        'max_retries': 3,
        'verify_ssl': True,
        'allowed_domains': event.get('allowed_domains', [])
    }
    
    if 'url' in event:
        result = fetch_and_display_url_content(
            url=event['url'],
            config=config,
            display=False,
            method=event.get('method', 'GET'),
            headers=event.get('headers'),
            params=event.get('params'),
            data=event.get('body'),
            auth=event.get('auth'),
            provider=event.get('provider')
        )
        
        return {
            'statusCode': 200 if result['success'] else 500,
            'body': json.dumps(result),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    
    elif 'Records' in event:
        results = []
        processor = WebhookProcessor(config)
        
        for record in event['Records']:
            if 'body' in record:
                try:
                    webhook_data = json.loads(record['body'])
                    result = processor.process_webhook(webhook_data)
                    results.append(result)
                except json.JSONDecodeError:
                    results.append({
                        'success': False,
                        'error': 'Invalid JSON in message body',
                        'timestamp': datetime.utcnow().isoformat()
                    })
        
        return {
            'statusCode': 200,
            'body': json.dumps({'results': results}),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid event format',
                'timestamp': datetime.utcnow().isoformat()
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }