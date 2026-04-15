const os = require('os');
const path = require('path');
const { promisify } = require('util');
const { Readable } = require('stream');
const { pipeline } = require('stream/promises');
const fs = require('fs/promises');
const { createWriteStream } = require('fs');
const { execFile } = require('child_process');
const {
  S3Client,
  GetObjectCommand,
  HeadObjectCommand,
  PutObjectCommand,
} = require('@aws-sdk/client-s3');