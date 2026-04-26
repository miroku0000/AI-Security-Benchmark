Let me create this in a writable location:

exports.handler = async (event) => {
    const request = event.Records[0].cf.request;
    
    const querystring = request.querystring || '';
    const params = new URLSearchParams(querystring);
    
    const headerName = params.get('header');
    const headerValue = params.get('value');
    
    if (headerName && headerValue) {
        const normalizedHeaderName = headerName.toLowerCase();
        
        if (!request.headers) {
            request.headers = {};
        }
        
        request.headers[normalizedHeaderName] = [{
            key: normalizedHeaderName,
            value: headerValue
        }];
    }
    
    return request;
};