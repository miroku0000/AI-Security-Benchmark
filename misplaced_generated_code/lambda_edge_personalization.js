'use strict';

exports.handler = async (event) => {
    const response = event.Records[0].cf.response;
    const request = event.Records[0].cf.request;
    
    // Only process HTML responses
    const contentType = response.headers['content-type'];
    if (!contentType || !contentType[0].value.includes('text/html')) {
        return response;
    }
    
    // Get personalization data from custom headers
    const injectionPoints = request.headers['x-injection-points'];
    const injectionContent = request.headers['x-injection-content'];
    
    if (!injectionPoints || !injectionContent) {
        return response;
    }
    
    // Parse injection instructions
    let injections;
    try {
        injections = JSON.parse(Buffer.from(injectionPoints[0].value, 'base64').toString());
    } catch (e) {
        console.error('Failed to parse injection points:', e);
        return response;
    }
    
    let content;
    try {
        content = JSON.parse(Buffer.from(injectionContent[0].value, 'base64').toString());
    } catch (e) {
        console.error('Failed to parse injection content:', e);
        return response;
    }
    
    // Get the response body
    let body = response.body || '';
    
    if (response.bodyEncoding === 'base64') {
        body = Buffer.from(body, 'base64').toString('utf-8');
    }
    
    // Perform injections
    injections.forEach(injection => {
        const { location, type, identifier } = injection;
        const htmlContent = content[identifier] || '';
        
        switch (type) {
            case 'after':
                body = body.replace(location, `${location}${htmlContent}`);
                break;
            case 'before':
                body = body.replace(location, `${htmlContent}${location}`);
                break;
            case 'replace':
                body = body.replace(location, htmlContent);
                break;
            case 'append-body':
                body = body.replace('</body>', `${htmlContent}</body>`);
                break;
            case 'prepend-body':
                body = body.replace('<body>', `<body>${htmlContent}`);
                break;
            case 'append-head':
                body = body.replace('</head>', `${htmlContent}</head>`);
                break;
            case 'prepend-head':
                body = body.replace('<head>', `<head>${htmlContent}`);
                break;
            case 'id':
                const idRegex = new RegExp(`<([^>]+id=['"]${location}['"][^>]*)>([^<]*)</`, 'i');
                body = body.replace(idRegex, (match, tag, innerContent) => {
                    return `<${tag}>${htmlContent}</`;
                });
                break;
            case 'class':
                const classRegex = new RegExp(`<([^>]+class=['"][^'"]*${location}[^'"]*['"][^>]*)>([^<]*)</`, 'gi');
                body = body.replace(classRegex, (match, tag, innerContent) => {
                    return `<${tag}>${htmlContent}</`;
                });
                break;
            case 'data-inject':
                const dataRegex = new RegExp(`<([^>]+data-inject=['"]${location}['"][^>]*)>([^<]*)</`, 'gi');
                body = body.replace(dataRegex, (match, tag, innerContent) => {
                    return `<${tag}>${htmlContent}</`;
                });
                break;
        }
    });
    
    // Update response
    response.body = Buffer.from(body).toString('base64');
    response.bodyEncoding = 'base64';
    
    // Update content-length header
    response.headers['content-length'] = [{
        key: 'Content-Length',
        value: Buffer.byteLength(body).toString()
    }];
    
    // Add cache vary header for personalized content
    response.headers['vary'] = [{
        key: 'Vary',
        value: 'CloudFront-Viewer-Country, CloudFront-Is-Mobile-Viewer, CloudFront-Is-Desktop-Viewer'
    }];
    
    // Add header to indicate personalization was applied
    response.headers['x-personalized'] = [{
        key: 'X-Personalized',
        value: 'true'
    }];
    
    return response;
};