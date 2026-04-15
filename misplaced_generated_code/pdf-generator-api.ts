import express, { Request, Response } from 'express';
import puppeteer from 'puppeteer';
import path from 'path';
import fs from 'fs/promises';
import crypto from 'crypto';
import { URL } from 'url';

const app = express();
app.use(express.json());

const OUTPUT_DIR = path.join(__dirname, 'generated-pdfs');
const ALLOWED_DOMAINS = [
  'example.com',
  'docs.company.com',
  'internal.company.com'
];

// Ensure output directory exists
async function ensureOutputDir() {
  try {
    await fs.mkdir(OUTPUT_DIR, { recursive: true });
  } catch (error) {
    console.error('Failed to create output directory:', error);
  }
}

// Validate URL
function isValidUrl(urlString: string): boolean {
  try {
    const url = new URL(urlString);
    // Only allow HTTP/HTTPS protocols
    if (!['http:', 'https:'].includes(url.protocol)) {
      return false;
    }
    // Check against allowed domains
    const hostname = url.hostname.toLowerCase();
    return ALLOWED_DOMAINS.some(domain => 
      hostname === domain || hostname.endsWith(`.${domain}`)
    );
  } catch {
    return false;
  }
}

// Sanitize filename
function sanitizeFilename(filename: string): string {
  // Remove path traversal attempts and special characters
  const base = path.basename(filename);
  const sanitized = base.replace(/[^a-zA-Z0-9_-]/g, '_');
  
  // Ensure .pdf extension
  if (!sanitized.endsWith('.pdf')) {
    return `${sanitized}.pdf`;
  }
  return sanitized;
}

// Generate PDF from URL
async function generatePDF(url: string, outputPath: string): Promise<void> {
  let browser;
  try {
    browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=IsolateOrigins',
        '--disable-site-isolation-trials'
      ]
    });

    const page = await browser.newPage();
    
    // Set timeout for page load
    await page.goto(url, { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });

    // Generate PDF with options
    await page.pdf({
      path: outputPath,
      format: 'A4',
      printBackground: true,
      margin: {
        top: '20mm',
        right: '15mm',
        bottom: '20mm',
        left: '15mm'
      }
    });

  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// API endpoint
app.post('/api/generate-pdf', async (req: Request, res: Response) => {
  try {
    const { url, filename } = req.body;

    // Validate input
    if (!url || !filename) {
      return res.status(400).json({
        error: 'Missing required parameters: url and filename'
      });
    }

    // Validate URL
    if (!isValidUrl(url)) {
      return res.status(400).json({
        error: 'Invalid or unauthorized URL'
      });
    }

    // Sanitize filename
    const safeFilename = sanitizeFilename(filename);
    
    // Generate unique ID for this request
    const requestId = crypto.randomBytes(16).toString('hex');
    const tempFilename = `${requestId}_${safeFilename}`;
    const outputPath = path.join(OUTPUT_DIR, tempFilename);

    // Ensure output directory exists
    await ensureOutputDir();

    // Generate PDF
    await generatePDF(url, outputPath);

    // Read the generated PDF
    const pdfBuffer = await fs.readFile(outputPath);

    // Clean up temporary file
    await fs.unlink(outputPath);

    // Send PDF as response
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename="${safeFilename}"`);
    res.send(pdfBuffer);

  } catch (error) {
    console.error('PDF generation error:', error);
    res.status(500).json({
      error: 'Failed to generate PDF',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'pdf-generator' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`PDF Generator API running on port ${PORT}`);
});