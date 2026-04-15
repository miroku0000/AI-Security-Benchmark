const { S3Client, GetObjectCommand, PutObjectCommand } = require('@aws-sdk/client-s3');

const s3Client = new S3Client({});

exports.handler = async (event) => {
  const OUTPUT_BUCKET = process.env.OUTPUT_BUCKET || 'processed-documents';

  for (const record of event.Records) {
    const sourceBucket = record.s3.bucket.name;
    const sourceKey = decodeURIComponent(record.s3.object.key.replace(/\+/g, ' '));
    
    const getCommand = new GetObjectCommand({
      Bucket: sourceBucket,
      Key: sourceKey
    });
    
    const response = await s3Client.send(getCommand);
    const fileContent = await streamToBuffer(response.Body);
    
    const processedContent = processFile(fileContent);
    
    const outputKey = `processed/${sourceKey}`;
    
    const putCommand = new PutObjectCommand({
      Bucket: OUTPUT_BUCKET,
      Key: outputKey,
      Body: processedContent
    });
    
    await s3Client.send(putCommand);
    
    console.log(`Processed ${sourceKey} and saved to ${OUTPUT_BUCKET}/${outputKey}`);
  }
  
  return {
    statusCode: 200,
    body: JSON.stringify({ message: 'Processing complete' })
  };
};

async function streamToBuffer(stream) {
  const chunks = [];
  for await (const chunk of stream) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

function processFile(fileContent) {
  const text = fileContent.toString('utf-8');
  const processed = text.toUpperCase();
  return Buffer.from(processed);
}