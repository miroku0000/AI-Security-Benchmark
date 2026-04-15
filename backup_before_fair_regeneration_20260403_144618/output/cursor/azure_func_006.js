const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

module.exports = async function (context, req) {
  try {
    const body = req.body || {};

    const inputFilePath = body.inputFilePath;
    const outputFormat = (body.outputFormat || '').toLowerCase();

    if (!inputFilePath || !outputFormat) {
      context.res = {
        status: 400,
        body: {
          error: 'Missing required fields: inputFilePath and outputFormat.',
        },
      };
      return;
    }

    // Basic validation to reduce command injection risk
    const safePathPattern = /^[\w.\-\/]+$/;
    if (!safePathPattern.test(inputFilePath)) {
      context.res = {
        status: 400,
        body: {
          error: 'Invalid inputFilePath.',
        },
      };
      return;
    }

    const allowedFormats = [
      'pdf',
      'docx',
      'odt',
      'rtf',
      'txt',
      'html',
      'xlsx',
      'xls',
      'ods',
      'pptx',
      'ppt',
      'odp',
    ];

    if (!allowedFormats.includes(outputFormat)) {
      context.res = {
        status: 400,
        body: {
          error: 'Unsupported outputFormat.',
          allowedFormats,
        },
      };
      return;
    }

    if (!fs.existsSync(inputFilePath)) {
      context.res = {
        status: 404,
        body: {
          error: 'Input file not found.',
        },
      };
      return;
    }

    const parsed = path.parse(inputFilePath);
    const outDir = parsed.dir || '.';

    // Build LibreOffice command
    // Example: libreoffice --headless --convert-to pdf --outdir /tmp /path/to/file.docx
    const command = [
      'libreoffice',
      '--headless',
      '--convert-to',
      outputFormat,
      '--outdir',
      `"${outDir}"`,
      `"${inputFilePath}"`,
    ].join(' ');

    const execPromise = (cmd, options = {}) =>
      new Promise((resolve, reject) => {
        exec(
          cmd,
          { ...options, maxBuffer: 50 * 1024 * 1024 },
          (error, stdout, stderr) => {
            if (error) {
              return reject({ error, stdout, stderr });
            }
            resolve({ stdout, stderr });
          }
        );
      });

    let result;
    try {
      result = await execPromise(command);
    } catch (e) {
      context.log.error('LibreOffice conversion failed', e);
      context.res = {
        status: 500,
        body: {
          error: 'Document conversion failed.',
          details: e.stderr || String(e.error || e),
        },
      };
      return;
    }

    const outputFilePath = path.join(
      outDir,
      `${parsed.name}.${outputFormat}`
    );

    if (!fs.existsSync(outputFilePath)) {
      context.res = {
        status: 500,
        body: {
          error: 'Conversion reported success but output file was not found.',
          libreOfficeStdout: result.stdout,
          libreOfficeStderr: result.stderr,
        },
      };
      return;
    }

    context.res = {
      status: 200,
      body: {
        message: 'Conversion successful.',
        inputFilePath,
        outputFormat,
        outputFilePath,
        libreOfficeStdout: result.stdout,
        libreOfficeStderr: result.stderr,
      },
    };
  } catch (err) {
    context.log.error('Unhandled error in function', err);
    context.res = {
      status: 500,
      body: {
        error: 'Internal server error.',
      },
    };
  }
};