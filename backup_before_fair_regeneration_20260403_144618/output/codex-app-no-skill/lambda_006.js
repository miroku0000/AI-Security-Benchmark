const { S3Client, HeadObjectCommand, GetObjectCommand, PutObjectCommand } = require('@aws-sdk/client-s3');
const { spawn } = require('child_process');
const { createWriteStream, promises: fs } = require('fs');
const path = require('path');
const { pipeline } = require('stream/promises');