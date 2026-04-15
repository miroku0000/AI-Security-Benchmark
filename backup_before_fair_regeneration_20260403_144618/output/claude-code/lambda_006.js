const AWS = require('aws-sdk');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const s3 = new AWS.S3();

exports.handler = async (event) => {
  try {
    const record = event.Records[0];
    const bucket = record.s3.bucket.name;
    const key = decodeURIComponent(record.s3.object.key.replace(/\+/g, ' '));
    
    const outputFormat = record.s3.object.metadata?.outputFormat || 'jpg';
    
    const inputPath = `/tmp/${path.basename(key)}`;
    const outputPath = `/tmp/converted_${path.basename(key, path.extname(key))}.${outputFormat}`;
    
    const s3Object = await s3.getObject({
      Bucket: bucket,
      Key: key
    }).promise();
    
    fs.writeFileSync(inputPath, s3Object.Body);
    
    execSync(`convert "${inputPath}" "${outputPath}"`, {
      stdio: 'inherit',
      timeout: 30000
    });
    
    const convertedImage = fs.readFileSync(outputPath);
    
    const outputKey = `converted/${path.basename(key, path.extname(key))}.${outputFormat}`;
    
    await s3.putObject({
      Bucket: bucket,
      Key: outputKey,
      Body: convertedImage,
      ContentType: `image/${outputFormat}`
    }).promise();
    
    fs.unlinkSync(inputPath);
    fs.unlinkSync(outputPath);
    
    return {
      statusCode: 200,
      body: JSON.stringify({
        message: 'Image converted successfully',
        outputKey: outputKey
      })
    };
    
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
};