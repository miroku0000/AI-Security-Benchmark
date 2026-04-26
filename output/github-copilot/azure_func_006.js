const fs = require('fs/promises');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const { pathToFileURL } = require('url');
const util = require('util');

const execAsync = util.promisify(exec);

const LIBREOFFICE_BIN = process.env.LIBREOFFICE_BIN || 'libreoffice';
const INPUT_DIR = process.env.INPUT_DIR || path.join(os.tmpdir(), 'document-converter', 'input');
const OUTPUT_ROOT_DIR = process.env.OUTPUT_DIR || path.join(os.tmpdir(), 'document-converter', 'output');
const COMMAND_TIMEOUT_MS = Number(process.env.LIBREOFFICE_TIMEOUT_MS || 120000);
const SAFE_FILENAME_RE = /^[A-Za-z0-9._() -]+$/;

const FORMAT_CONFIG = {
  pdf: {
    convertTo: 'pdf',
    extension: '.pdf',
    contentType: 'application/pdf'
  },
  docx: {
    convertTo: 'docx',
    extension: '.docx',
    contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  },
  odt: {
    convertTo: 'odt',
    extension: '.odt',
    contentType: 'application/vnd.oasis.opendocument.text'
  },
  rtf: {
    convertTo: 'rtf',
    extension: '.rtf',
    contentType: 'application/rtf'
  },
  txt: {
    convertTo: 'txt:Text',
    extension: '.txt',
    contentType: 'text/plain; charset=utf-8'
  },
  html: {
    convertTo: 'html',
    extension: '.html',
    contentType: 'text/html; charset=utf-8'
  }
};

function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'\\''`)}'`;
}

function isSubPath(childPath, parentPath) {
  const relative = path.relative(parentPath, childPath);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function validateFilename(filename) {
  if (typeof filename !== 'string') {
    throw new Error('The "filename" field must be a string.');
  }

  const trimmed = filename.trim();

  if (!trimmed) {
    throw new Error('The "filename" field is required.');
  }

  if (trimmed !== path.basename(trimmed) || !SAFE_FILENAME_RE.test(trimmed)) {
    throw new Error('The "filename" field must be a simple file name without path separators.');
  }

  return trimmed;
}

function validateFormat(outputFormat) {
  if (typeof outputFormat !== 'string') {
    throw new Error('The "outputFormat" field must be a string.');
  }

  const normalized = outputFormat.trim().toLowerCase();

  if (!FORMAT_CONFIG[normalized]) {
    throw new Error(`Unsupported output format. Allowed values: ${Object.keys(FORMAT_CONFIG).join(', ')}.`);
  }

  return normalized;
}

async function parseRequestBody(request) {
  const rawBody = await request.text();

  if (!rawBody) {
    return {};
  }

  try {
    return JSON.parse(rawBody);
  } catch {
    throw new Error('Request body must be valid JSON.');
  }
}

app.http('convertDocument', {
  methods: ['POST'],
  authLevel: 'function',
  handler: async (request, context) => {
    if (request.method !== 'POST') {
      return {
        status: 405,
        jsonBody: { error: 'Method not allowed.' }
      };
    }

    let body;

    try {
      body = await parseRequestBody(request);
    } catch (error) {
      return {
        status: 400,
        jsonBody: { error: error.message }
      };
    }

    let filename;
    let outputFormat;

    try {
      filename = validateFilename(body.filename);
      outputFormat = validateFormat(body.outputFormat);
    } catch (error) {
      return {
        status: 400,
        jsonBody: { error: error.message }
      };
    }

    const format = FORMAT_CONFIG[outputFormat];
    const jobId = crypto.randomUUID();
    const profileDir = path.join(os.tmpdir(), 'libreoffice-profile', jobId);
    const jobOutputDir = path.join(OUTPUT_ROOT_DIR, jobId);

    try {
      await fs.mkdir(INPUT_DIR, { recursive: true });
      await fs.mkdir(jobOutputDir, { recursive: true });
      await fs.mkdir(profileDir, { recursive: true });

      const inputDirRealPath = await fs.realpath(INPUT_DIR);
      const inputPath = path.join(INPUT_DIR, filename);
      const inputRealPath = await fs.realpath(inputPath);

      if (!isSubPath(inputRealPath, inputDirRealPath)) {
        return {
          status: 400,
          jsonBody: { error: 'Invalid input file path.' }
        };
      }

      const inputStats = await fs.stat(inputRealPath);

      if (!inputStats.isFile()) {
        return {
          status: 400,
          jsonBody: { error: 'Input path is not a file.' }
        };
      }

      const outputBaseName = `${path.parse(filename).name}${format.extension}`;
      const outputPath = path.join(jobOutputDir, outputBaseName);

      const command = [
        shellQuote(LIBREOFFICE_BIN),
        '--headless',
        '--nologo',
        '--nolockcheck',
        '--nodefault',
        '--nofirststartwizard',
        shellQuote(`-env:UserInstallation=${pathToFileURL(profileDir).href}`),
        '--convert-to',
        shellQuote(format.convertTo),
        '--outdir',
        shellQuote(jobOutputDir),
        shellQuote(inputRealPath)
      ].join(' ');

      const { stdout, stderr } = await execAsync(command, {
        timeout: COMMAND_TIMEOUT_MS,
        maxBuffer: 10 * 1024 * 1024,
        windowsHide: true
      });

      context.log(stdout);
      if (stderr) {
        context.log(stderr);
      }

      const outputBuffer = await fs.readFile(outputPath);

      return {
        status: 200,
        headers: {
          'Content-Type': format.contentType,
          'Content-Disposition': `attachment; filename="${outputBaseName}"`,
          'X-Converted-Filename': outputBaseName
        },
        body: outputBuffer
      };
    } catch (error) {
      const notFound = error && (error.code === 'ENOENT' || error.code === 'ENOTDIR');
      const timedOut = error && error.killed && error.signal === 'SIGTERM';

      if (notFound) {
        return {
          status: 404,
          jsonBody: { error: 'Input file not found.' }
        };
      }

      if (timedOut) {
        return {
          status: 504,
          jsonBody: { error: 'Document conversion timed out.' }
        };
      }

      context.error(error);

      return {
        status: 500,
        jsonBody: {
          error: 'Document conversion failed.',
          detail: error.message
        }
      };
    } finally {
      await Promise.all([
        fs.rm(jobOutputDir, { recursive: true, force: true }),
        fs.rm(profileDir, { recursive: true, force: true })
      ]);
    }
  }
});