function extractInjectionsFromHeaders(headers) {
  const injections = [];
  const injectionPattern = /^x-inject-\d+$/i;

  for (const headerName in headers) {
    if (injectionPattern.test(headerName)) {
      const headerValues = headers[headerName];
      if (Array.isArray(headerValues) && headerValues.length > 0) {
        const headerValue = headerValues[0].value;
        
        try {
          const injection = JSON.parse(decodeURIComponent(headerValue));
          
          if (injection.selector && injection.content && injection.position) {
            injections.push({
              selector: injection.selector,
              content: injection.content,
              position: injection.position.toLowerCase()
            });
          }
        } catch (err) {
          console.warn(`Failed to parse injection header ${headerName}:`, err);
        }
      }
    }
  }

  return injections;
}

function injectContent(html, selector, content, position) {
  const selectorRegex = createSelectorRegex(selector);

  if (!selectorRegex) {
    return html;
  }

  switch (position) {
    case 'before':
      return html.replace(selectorRegex, (match) => content + match);
    
    case 'after':
      return html.replace(selectorRegex, (match) => match + content);
    
    case 'replace':
      return html.replace(selectorRegex, content);
    
    case 'append':
      return injectAtElement(html, selector, content, 'append');
    
    case 'prepend':
      return injectAtElement(html, selector, content, 'prepend');
    
    default:
      return html;
  }
}

function createSelectorRegex(selector) {
  if (!selector) return null;

  if (selector.startsWith('#')) {
    const id = selector.substring(1).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`<[^>]+id=["']?${id}["']?[^>]*>`, 'i');
  }

  if (selector.startsWith('.')) {
    const className = selector.substring(1).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`<[^>]+class=["']?[^"']*${className}[^"']*["']?[^>]*>`, 'i');
  }

  const tag = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`<${tag}[^>]*>`, 'i');
}

function injectAtElement(html, selector, content, position) {
  if (selector.startsWith('#')) {
    const id = selector.substring(1).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const openTagRegex = new RegExp(`(<[^>]+id=["']?${id}["']?[^>]*>)`, 'i');
    const match = html.match(openTagRegex);
    
    if (match) {
      const closingTagRegex = createClosingTagRegex(match[0]);
      const fullMatch = new RegExp(
        match[0].replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '.*?' + closingTagRegex,
        'is'
      );
      
      const elementMatch = html.match(fullMatch);
      if (elementMatch) {
        const element = elementMatch[0];
        if (position === 'append') {
          const closingTag = element.match(closingTagRegex)[0];
          const modified = element.replace(closingTagRegex, content + closingTag);
          return html.replace(element, modified);
        } else if (position === 'prepend') {
          const modified = element.replace(openTagRegex, '$1' + content);
          return html.replace(element, modified);
        }
      }
    }
  }

  return html;
}

function createClosingTagRegex(openTag) {
  const tagMatch = openTag.match(/<(\w+)/);
  if (!tagMatch) return /<\/[^>]+>/;
  
  const tagName = tagMatch[1];
  return new RegExp(`</${tagName}>`, 'i');
}


Viewer request function to set injection headers:

exports.handler = async (event) => {
  const request = event.Records[0].cf.request;
  const userContext = request.clientIp;
  
  request.headers['x-inject-0'] = [{
    key: 'X-Inject-0',
    value: JSON.stringify({
      selector: '#user-banner',
      content: '<div class="personalized-greeting">Welcome back!</div>',
      position: 'prepend'
    }).replace(/"/g, '%22')
  }];

  request.headers['x-inject-1'] = [{
    key: 'X-Inject-1',
    value: JSON.stringify({
      selector: '.product-recommendations',
      content: '<div class="rec-item">Recommended product</div>',
      position: 'append'
    }).replace(/"/g, '%22')
  }];

  return request;
};


Test suite for origin response handler:

const assert = require('assert');
const { handler } = require('./lambda_edge_origin_response.js');

const createMockEvent = (html, headers = {}) => ({
  Records: [{
    cf: {
      response: {
        status: '200',
        headers: {
          'content-type': [{ key: 'Content-Type', value: 'text/html; charset=utf-8' }],
          'content-length': [{ key: 'Content-Length', value: html.length.toString() }],
          ...Object.keys(headers).reduce((acc, key) => {
            acc[key] = [{ key, value: headers[key] }];
            return acc;
          }, {})
        },
        body: Buffer.from(html, 'utf-8').toString('base64'),
        bodyEncoding: 'base64'
      },
      request: {
        headers: {
          ...Object.keys(headers).reduce((acc, key) => {
            acc[key.toLowerCase()] = [{ key, value: headers[key] }];
            return acc;
          }, {})
        }
      }
    }
  }]
});

describe('Lambda@Edge Origin Response Handler', () => {
  it('should return response unchanged if not HTML', async () => {
    const event = {
      Records: [{
        cf: {
          response: {
            status: '200',
            headers: {
              'content-type': [{ key: 'Content-Type', value: 'application/json' }]
            },
            body: '{"key": "value"}',
            bodyEncoding: 'text'
          },
          request: { headers: {} }
        }
      }]
    };
    
    const result = await handler(event);
    assert.strictEqual(result.body, '{"key": "value"}');
  });

  it('should inject content before selector', async () => {
    const html = '<html><body><div id="target">Original</div></body></html>';
    const injectionHeader = JSON.stringify({
      selector: '#target',
      content: '<span>Injected</span>',
      position: 'before'
    }).replace(/"/g, '%22');
    
    const event = createMockEvent(html, { 'x-inject-0': injectionHeader });
    const result = await handler(event);
    const decodedBody = Buffer.from(result.body, 'base64').toString('utf-8');
    
    assert(decodedBody.includes('<span>Injected</span><div id="target">'));
  });

  it('should inject content after selector', async () => {
    const html = '<html><body><div id="target">Original</div></body></html>';
    const injectionHeader = JSON.stringify({
      selector: '#target',
      content: '<span>Injected</span>',
      position: 'after'
    }).replace(/"/g, '%22');
    
    const event = createMockEvent(html, { 'x-inject-0': injectionHeader });
    const result = await handler(event);
    const decodedBody = Buffer.from(result.body, 'base64').toString('utf-8');
    
    assert(decodedBody.includes('</div><span>Injected</span>'));
  });

  it('should replace selector element', async () => {
    const html = '<html><body><div id="target">Original</div></body></html>';
    const injectionHeader = JSON.stringify({
      selector: '#target',
      content: '<div id="target">Replaced</div>',
      position: 'replace'
    }).replace(/"/g, '%22');
    
    const event = createMockEvent(html, { 'x-inject-0': injectionHeader });
    const result = await handler(event);
    const decodedBody = Buffer.from(result.body, 'base64').toString('utf-8');
    
    assert(decodedBody.includes('Replaced'));
    assert(!decodedBody.includes('Original'));
  });

  it('should handle multiple injections', async () => {
    const html = '<html><body><div id="a">A</div><div id="b">B</div></body></html>';
    const injection0 = JSON.stringify({
      selector: '#a',
      content: '<span>1</span>',
      position: 'after'
    }).replace(/"/g, '%22');
    
    const injection1 = JSON.stringify({
      selector: '#b',
      content: '<span>2</span>',
      position: 'after'
    }).replace(/"/g, '%22');
    
    const event = createMockEvent(html, { 'x-inject-0': injection0, 'x-inject-1': injection1 });
    const result = await handler(event);
    const decodedBody = Buffer.from(result.body, 'base64').toString('utf-8');
    
    assert(decodedBody.includes('<span>1</span>'));
    assert(decodedBody.includes('<span>2</span>'));
  });

  it('should update content-length header', async () => {
    const html = '<html><body><div id="target">Test</div></body></html>';
    const injectionHeader = JSON.stringify({
      selector: '#target',
      content: '<span>Injected content that is longer</span>',
      position: 'before'
    }).replace(/"/g, '%22');
    
    const event = createMockEvent(html, { 'x-inject-0': injectionHeader });
    const result = await handler(event);
    const newLength = parseInt(result.headers['content-length'][0].value);
    
    assert(newLength > html.length);
  });

  it('should handle class selectors', async () => {
    const html = '<html><body><div class="highlight">Content</div></body></html>';
    const injectionHeader = JSON.stringify({
      selector: '.highlight',
      content: '<span>Pre</span>',
      position: 'before'
    }).replace(/"/g, '%22');
    
    const event = createMockEvent(html, { 'x-inject-0': injectionHeader });
    const result = await handler(event);
    const decodedBody = Buffer.from(result.body, 'base64').toString('utf-8');
    
    assert(decodedBody.includes('<span>Pre</span><div class="highlight">'));
  });

  it('should handle tag selectors', async () => {
    const html = '<html><body><header>Title</header></body></html>';
    const injectionHeader = JSON.stringify({
      selector: 'header',
      content: '<nav>Menu</nav>',
      position: 'after'
    }).replace(/"/g, '%22');
    
    const event = createMockEvent(html, { 'x-inject-0': injectionHeader });
    const result = await handler(event);
    const decodedBody = Buffer.from(result.body, 'base64').toString('utf-8');
    
    assert(decodedBody.includes('</header><nav>Menu</nav>'));
  });

  it('should gracefully handle malformed injection headers', async () => {
    const html = '<html><body><div>Content</div></body></html>';
    const event = createMockEvent(html, { 'x-inject-0': 'invalid-json' });
    const result = await handler(event);
    const decodedBody = Buffer.from(result.body, 'base64').toString('utf-8');
    
    assert.strictEqual(decodedBody, html);
  });

  it('should escape special characters in regex patterns', async () => {
    const html = '<html><body><div id="test.id">Content</div></body></html>';
    const injectionHeader = JSON.stringify({
      selector: '#test.id',
      content: '<span>Injected</span>',
      position: 'before'
    }).replace(/"/g, '%22');
    
    const event = createMockEvent(html, { 'x-inject-0': injectionHeader });
    const result = await handler(event);
    const decodedBody = Buffer.from(result.body, 'base64').toString('utf-8');
    
    assert(decodedBody.includes('<span>Injected</span>'));
  });
});


CloudFormation template to deploy:

AWSTemplateFormatVersion: '2010-09-09'
Description: 'Lambda@Edge for CloudFront personalization'

Resources:
  LambdaEdgeExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service:
                - lambda.amazonaws.com
                - edgelambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

  OriginResponseFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: cloudfront-personalization-origin-response
      Runtime: nodejs18.x
      Handler: index.handler
      Role: !GetAtt LambdaEdgeExecutionRole.Arn
      Code:
        ZipFile: |
          exports.handler = async (event) => {
            const response = event.Records[0].cf.response;
            const request = event.Records[0].cf.request;
            const headers = response.headers;

            const isHtml = headers['content-type'] && 
              headers['content-type'][0].value.includes('text/html');

            if (!isHtml || response.status !== '200') {
              return response;
            }

            const bodyEncoding = response.bodyEncoding || 'text';
            const body = response.body || '';

            let htmlContent;
            try {
              if (bodyEncoding === 'base64') {
                htmlContent = Buffer.from(body, 'base64').toString('utf-8');
              } else {
                htmlContent = body;
              }
            } catch (err) {
              console.error('Error decoding response body:', err);
              return response;
            }

            const injections = extractInjectionsFromHeaders(request.headers);

            if (injections.length === 0) {
              return response;
            }

            let modifiedHtml = htmlContent;

            for (const injection of injections) {
              modifiedHtml = injectContent(
                modifiedHtml,
                injection.selector,
                injection.content,
                injection.position
              );
            }

            const modifiedBody = Buffer.from(modifiedHtml, 'utf-8').toString('base64');

            response.body = modifiedBody;
            response.bodyEncoding = 'base64';

            if (headers['content-length']) {
              headers['content-length'][0].value = Buffer.byteLength(modifiedHtml, 'utf-8').toString();
            }

            return response;
          };

          function extractInjectionsFromHeaders(headers) {
            const injections = [];
            const injectionPattern = /^x-inject-\d+$/i;

            for (const headerName in headers) {
              if (injectionPattern.test(headerName)) {
                const headerValues = headers[headerName];
                if (Array.isArray(headerValues) && headerValues.length > 0) {
                  const headerValue = headerValues[0].value;
                  
                  try {
                    const injection = JSON.parse(decodeURIComponent(headerValue));
                    
                    if (injection.selector && injection.content && injection.position) {
                      injections.push({
                        selector: injection.selector,
                        content: injection.content,
                        position: injection.position.toLowerCase()
                      });
                    }
                  } catch (err) {
                    console.warn(`Failed to parse injection header ${headerName}:`, err);
                  }
                }
              }
            }

            return injections;
          }

          function injectContent(html, selector, content, position) {
            const selectorRegex = createSelectorRegex(selector);

            if (!selectorRegex) {
              return html;
            }

            switch (position) {
              case 'before':
                return html.replace(selectorRegex, (match) => content + match);
              
              case 'after':
                return html.replace(selectorRegex, (match) => match + content);
              
              case 'replace':
                return html.replace(selectorRegex, content);
              
              case 'append':
                return injectAtElement(html, selector, content, 'append');
              
              case 'prepend':
                return injectAtElement(html, selector, content, 'prepend');
              
              default:
                return html;
            }
          }

          function createSelectorRegex(selector) {
            if (!selector) return null;

            if (selector.startsWith('#')) {
              const id = selector.substring(1).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
              return new RegExp(`<[^>]+id=["']?${id}["']?[^>]*>`, 'i');
            }

            if (selector.startsWith('.')) {
              const className = selector.substring(1).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
              return new RegExp(`<[^>]+class=["']?[^"']*${className}[^"']*["']?[^>]*>`, 'i');
            }

            const tag = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            return new RegExp(`<${tag}[^>]*>`, 'i');
          }

          function injectAtElement(html, selector, content, position) {
            if (selector.startsWith('#')) {
              const id = selector.substring(1).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
              const openTagRegex = new RegExp(`(<[^>]+id=["']?${id}["']?[^>]*>)`, 'i');
              const match = html.match(openTagRegex);
              
              if (match) {
                const closingTagRegex = createClosingTagRegex(match[0]);
                const fullMatch = new RegExp(
                  match[0].replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '.*?' + closingTagRegex,
                  'is'
                );
                
                const elementMatch = html.match(fullMatch);
                if (elementMatch) {
                  const element = elementMatch[0];
                  if (position === 'append') {
                    const closingTag = element.match(closingTagRegex)[0];
                    const modified = element.replace(closingTagRegex, content + closingTag);
                    return html.replace(element, modified);
                  } else if (position === 'prepend') {
                    const modified = element.replace(openTagRegex, '$1' + content);
                    return html.replace(element, modified);
                  }
                }
              }
            }

            return html;
          }

          function createClosingTagRegex(openTag) {
            const tagMatch = openTag.match(/<(\w+)/);
            if (!tagMatch) return /<\/[^>]+>/;
            
            const tagName = tagMatch[1];
            return new RegExp(`</${tagName}>`, 'i');
          }

  OriginResponseFunctionVersion:
    Type: AWS::Lambda::Version
    Properties:
      FunctionName: !Ref OriginResponseFunction

  ViewerRequestFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: cloudfront-personalization-viewer-request
      Runtime: nodejs18.x
      Handler: index.handler
      Role: !GetAtt LambdaEdgeExecutionRole.Arn
      Code:
        ZipFile: |
          exports.handler = async (event) => {
            const request = event.Records[0].cf.request;
            
            request.headers['x-inject-0'] = [{
              key: 'X-Inject-0',
              value: JSON.stringify({
                selector: '#user-banner',
                content: '<div class="personalized-greeting">Welcome back!</div>',
                position: 'prepend'
              }).replace(/"/g, '%22')
            }];

            return request;
          };

  ViewerRequestFunctionVersion:
    Type: AWS::Lambda::Version
    Properties:
      FunctionName: !Ref ViewerRequestFunction

Outputs:
  OriginResponseFunctionArn:
    Value: !GetAtt OriginResponseFunctionVersion.FunctionArn
    Description: ARN of origin response Lambda@Edge function

  ViewerRequestFunctionArn:
    Value: !GetAtt ViewerRequestFunctionVersion.FunctionArn
    Description: ARN of viewer request Lambda@Edge function