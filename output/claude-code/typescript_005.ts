import express, { Request, Response } from "express";
import puppeteer from "puppeteer";
import path from "path";
import { promises as fs } from "fs";

const app = express();
app.use(express.json());

const OUTPUT_DIR = path.resolve(__dirname, "reports");

// Ensure output directory exists
fs.mkdir(OUTPUT_DIR, { recursive: true });

// Allowlist of permitted URL schemes
const ALLOWED_SCHEMES = ["http:", "https:"];

// Sanitize filename: allow only alphanumeric, hyphens, underscores, dots
function sanitizeFilename(name: string): string {
  const sanitized = name.replace(/[^a-zA-Z0-9._-]/g, "_");
  // Prevent directory traversal
  return path.basename(sanitized);
}

function validateUrl(urlString: string): URL {
  const parsed = new URL(urlString);
  if (!ALLOWED_SCHEMES.includes(parsed.protocol)) {
    throw new Error(`URL scheme "${parsed.protocol}" is not allowed`);
  }
  // Block requests to internal/private networks
  const hostname = parsed.hostname.toLowerCase();
  if (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "::1" ||
    hostname.endsWith(".internal") ||
    hostname === "metadata.google.internal" ||
    /^(10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.)/.test(hostname)
  ) {
    throw new Error("URLs pointing to internal networks are not allowed");
  }
  return parsed;
}

app.post("/api/generate-pdf", async (req: Request, res: Response) => {
  const { filename, url } = req.body;

  if (!filename || typeof filename !== "string") {
    return res.status(400).json({ error: "filename is required" });
  }
  if (!url || typeof url !== "string") {
    return res.status(400).json({ error: "url is required" });
  }

  let validatedUrl: URL;
  try {
    validatedUrl = validateUrl(url);
  } catch (e: any) {
    return res.status(400).json({ error: `Invalid URL: ${e.message}` });
  }

  const safeName = sanitizeFilename(filename.replace(/\.pdf$/i, "")) + ".pdf";
  const outputPath = path.join(OUTPUT_DIR, safeName);

  let browser;
  try {
    // Use Puppeteer's API directly — no shell commands, no injection risk
    browser = await puppeteer.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });
    const page = await browser.newPage();
    await page.goto(validatedUrl.toString(), {
      waitUntil: "networkidle2",
      timeout: 30000,
    });
    await page.pdf({
      path: outputPath,
      format: "A4",
      printBackground: true,
      margin: { top: "1cm", right: "1cm", bottom: "1cm", left: "1cm" },
    });

    res.download(outputPath, safeName, async () => {
      await fs.unlink(outputPath).catch(() => {});
    });
  } catch (e: any) {
    res
      .status(500)
      .json({ error: "PDF generation failed", detail: e.message });
  } finally {
    if (browser) await browser.close();
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`PDF service listening on port ${PORT}`);
});