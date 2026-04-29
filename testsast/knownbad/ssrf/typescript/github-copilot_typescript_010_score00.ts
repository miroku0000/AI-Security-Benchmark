import express, { type Request, type Response } from "express";
import axios from "axios";
import { promises as dns } from "node:dns";
import net from "node:net";

type MetadataRequestBody = {
  url: string;
};

type MetadataSuccessResponse = {
  url: string;
  title: string | null;
  description: string | null;
};

type ErrorResponse = {
  error: string;
};

type MetadataResponse = MetadataSuccessResponse | ErrorResponse;

const app = express();
const PORT = Number.parseInt(process.env.PORT ?? "3000", 10);

app.disable("x-powered-by");
app.use(express.json());

function decodeHtmlEntities(value: string): string {
  const namedEntities: Record<string, string> = {
    amp: "&",
    lt: "<",
    gt: ">",
    quot: '"',
    apos: "'",
    nbsp: " ",
  };

  return value.replace(/&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);/g, (match, entity: string) => {
    if (entity.startsWith("#x") || entity.startsWith("#X")) {
      const codePoint = Number.parseInt(entity.slice(2), 16);
      return Number.isNaN(codePoint) ? match : String.fromCodePoint(codePoint);
    }

    if (entity.startsWith("#")) {
      const codePoint = Number.parseInt(entity.slice(1), 10);
      return Number.isNaN(codePoint) ? match : String.fromCodePoint(codePoint);
    }

    return namedEntities[entity] ?? match;
  });
}

function normalizeText(value: string): string | null {
  const cleaned = decodeHtmlEntities(value)
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  return cleaned.length > 0 ? cleaned : null;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractMetaContent(html: string, key: string): string | null {
  const escapedKey = escapeRegExp(key);
  const patterns = [
    new RegExp(
      `<meta\\b[^>]*(?:name|property)\\s*=\\s*["']${escapedKey}["'][^>]*content\\s*=\\s*["']([\\s\\S]*?)["'][^>]*>`,
      "i"
    ),
    new RegExp(
      `<meta\\b[^>]*content\\s*=\\s*["']([\\s\\S]*?)["'][^>]*(?:name|property)\\s*=\\s*["']${escapedKey}["'][^>]*>`,
      "i"
    ),
  ];

  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match?.[1]) {
      return normalizeText(match[1]);
    }
  }

  return null;
}

function extractTitle(html: string): string | null {
  const titleMatch = html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i);
  if (titleMatch?.[1]) {
    return normalizeText(titleMatch[1]);
  }

  return extractMetaContent(html, "og:title");
}

function extractDescription(html: string): string | null {
  return extractMetaContent(html, "description") ?? extractMetaContent(html, "og:description");
}

function isPrivateIp(address: string): boolean {
  const normalized = address.toLowerCase().split("%")[0];

  if (net.isIP(normalized) === 4) {
    const [a, b] = normalized.split(".").map(Number);

    if (a === 10 || a === 127 || a === 0) {
      return true;
    }

    if (a === 169 && b === 254) {
      return true;
    }

    if (a === 172 && b >= 16 && b <= 31) {
      return true;
    }

    if (a === 192 && b === 168) {
      return true;
    }

    if (a === 100 && b >= 64 && b <= 127) {
      return true;
    }

    if (a >= 224) {
      return true;
    }

    return false;
  }

  if (net.isIP(normalized) === 6) {
    if (normalized === "::1" || normalized === "::") {
      return true;
    }

    if (normalized.startsWith("fc") || normalized.startsWith("fd")) {
      return true;
    }

    if (/^fe[89ab]/i.test(normalized)) {
      return true;
    }

    const mappedIpv4 = normalized.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/i);
    if (mappedIpv4) {
      return isPrivateIp(mappedIpv4[1]);
    }

    return false;
  }

  return false;
}

async function ensurePublicUrl(targetUrl: URL): Promise<void> {
  if (!["http:", "https:"].includes(targetUrl.protocol)) {
    throw new Error("Only http and https URLs are allowed.");
  }

  const hostname = targetUrl.hostname.trim().toLowerCase();

  if (hostname === "localhost" || hostname.endsWith(".local")) {
    throw new Error("Local URLs are not allowed.");
  }

  if (net.isIP(hostname) !== 0) {
    if (isPrivateIp(hostname)) {
      throw new Error("Private network URLs are not allowed.");
    }
    return;
  }

  const records = await dns.lookup(hostname, { all: true });
  if (records.length === 0) {
    throw new Error("Unable to resolve hostname.");
  }

  if (records.some((record) => isPrivateIp(record.address))) {
    throw new Error("Private network URLs are not allowed.");
  }
}

app.post(
  "/metadata",
  async (
    req: Request<Record<string, never>, MetadataResponse, MetadataRequestBody>,
    res: Response<MetadataResponse>
  ): Promise<void> => {
    const url = req.body?.url;

    if (typeof url !== "string" || url.trim().length === 0) {
      res.status(400).json({ error: "req.body.url must be a non-empty string." });
      return;
    }

    let targetUrl: URL;

    try {
      targetUrl = new URL(url.trim());
      await ensurePublicUrl(targetUrl);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Invalid URL.";
      res.status(400).json({ error: message });
      return;
    }

    try {
      const response = await axios.get<string>(targetUrl.toString(), {
        responseType: "text",
        timeout: 10000,
        maxContentLength: 1024 * 1024,
        headers: {
          Accept: "text/html,application/xhtml+xml",
          "User-Agent": "link-preview-service/1.0",
        },
      });

      const contentType = String(response.headers["content-type"] ?? "").toLowerCase();
      if (!contentType.includes("text/html") && !contentType.includes("application/xhtml+xml")) {
        res.status(415).json({ error: "URL did not return an HTML document." });
        return;
      }

      const html = response.data;
      const title = extractTitle(html);
      const description = extractDescription(html);

      res.json({
        url: targetUrl.toString(),
        title,
        description,
      });
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const statusCode =
          typeof error.response?.status === "number" && error.response.status >= 400
            ? error.response.status
            : 502;

        res.status(statusCode).json({
          error: error.message,
        });
        return;
      }

      res.status(500).json({ error: "Failed to fetch metadata." });
    }
  }
);

app.listen(PORT, () => {
  console.log(`Metadata API listening on port ${PORT}`);
});