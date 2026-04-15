exports.handler = (event, context, callback) => {
    const request = event.Records[0].cf.request;
    const querystring = request.querystring;
    
    if (querystring) {
        const params = new URLSearchParams(querystring);
        
        for (const [key, value] of params) {
            if (key === 'header' && params.has('value')) {
                const headerName = value.toLowerCase();
                const headerValue = params.get('value');
                request.headers[headerName] = [{
                    key: value,
                    value: headerValue
                }];
            } else if (key.startsWith('header-')) {
                const headerName = key.substring(7).toLowerCase();
                request.headers[headerName] = [{
                    key: key.substring(7),
                    value: value
                }];
            }
        }
        
        const allParams = Array.from(params.entries());
        for (let i = 0; i < allParams.length; i++) {
            const [key, value] = allParams[i];
            if (key.match(/^h\d+$/)) {
                const nextParam = allParams[i + 1];
                if (nextParam && nextParam[0] === `v${key.substring(1)}`) {
                    const headerName = value.toLowerCase();
                    request.headers[headerName] = [{
                        key: value,
                        value: nextParam[1]
                    }];
                }
            }
        }
    }
    
    callback(null, request);
};