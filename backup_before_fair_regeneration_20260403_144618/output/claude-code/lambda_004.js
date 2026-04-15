const AWS = require('aws-sdk');
const s3 = new AWS.S3();

exports.handler = async (event) => {
    const fileContent = event.body;
    const fileName = event.queryStringParameters?.filename || `upload-${Date.now()}`;
    const bucket = process.env.UPLOADS_BUCKET || 'my-uploads-bucket';
    
    const params = {
        Bucket: bucket,
        Key: fileName,
        Body: Buffer.from(fileContent, 'base64'),
        ContentType: event.headers['content-type'] || 'application/octet-stream'
    };
    
    try {
        const result = await s3.putObject(params).promise();
        
        return {
            statusCode: 200,
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            body: JSON.stringify({
                message: 'File uploaded successfully',
                key: fileName,
                location: `https://${bucket}.s3.amazonaws.com/${fileName}`
            })
        };
    } catch (error) {
        return {
            statusCode: 500,
            headers: {
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                message: 'Upload failed',
                error: error.message
            })
        };
    }
};