import express, { Request, Response } from "express";
import puppeteer from "puppeteer";

const app = express();
app.use(express.json({ limit: "1mb" }));

const PORT = Number(process.env.PORT || 3000);
const NAVIGATION_TIMEOUT_MS = Number(process.env.NAVIGATION_TIMEOUT_MS || 30000);
const ALLOWED_HOSTS = (process.env.ALLOWED_HOSTS || "")
  .split(",")
  .map((host) => host.trim().toLowerCase())
  .filter(Boolean);

function sanitizeFilename(input: unknown): string {
  const fallback = "report.pdf";
  if (typeof input !== "string" || input.trim() === "") return fallback;

  const cleaned = input
    .trim()
    .replace(/[/\\?%*:|"<>]/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 128);

  if (!cleaned) return fallback;
  return cleaned.toLowerCase().endsWith(".pdf") ? cleaned : `${cleaned}.pdf`;
}

function parseAndValidateUrl(input: unknown): URL {
  if (typeof input !== "string" || input.trim() === "") {
    throw new Error("url is required");
  }

  let parsed: URL;
  try {
    parsed = new URL(input);
  } catch {
    throw new Error("url must be a valid absolute URL");
  }

  if (parsed.protocol !== "https:") {
    throw new Error("only https URLs are allowed");
  }

  if (ALLOWED_HOSTS.length > 0 && !ALLOWED_HOSTS.includes(parsed.hostname.toLowerCase())) {
    throw new Error("url host is not allowed");
  }

  return parsed;
}

app.post("/reports/pdf", async (req: Request, res: Response) => {
  let browser;

  try {
    const url = parseAndValidateUrl(req.body?.url);
    const filename = sanitizeFilename(req.body?.filename);

    browser = await puppeteer.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });

    const page = await browser.newPage();
    await page.goto(url.toString(), {
      waitUntil: "networkidle2",
      timeout: NAVIGATION_TIMEOUT_MS,
    });

    const pdf = await page.pdf({
      format: "A4",
      printBackground: true,
      preferCSSPageSize: true,
    });

    res.setHeader("Content-Type", "application/pdf");
    res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
    res.status(200).send(pdf);
  } catch (error) {
    const message = error instanceof Error ? error.message : "failed to generate PDF";
    res.status(400).json({ error: message });
  } finally {
    if (browser) {
      await browser.close();
    }
  }
});

app.listen(PORT, () => {
  console.log(`PDF service listening on port ${PORT}`);
});