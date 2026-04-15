import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import crypto from "node:crypto";

const s3 = new S3Client({});

function getHeader(headers, name) {
  if (!headers) return undefined;
  const needle = name.toLowerCase();
  for (const [k, v] of Object.entries(headers)) {
    if (k && k.toLowerCase() === needle) return Array.isArray(v) ? v[0] : v;
  }
  return undefined;
}

function sanitizeFilename(name) {
  if (!name) return undefined;
  const base = String(name).split(/[\\/]/).pop();
  const cleaned = base.replace(/[^\w.\-()+@= ]+/g, "_").trim();
  return cleaned.length ? cleaned.slice(0, 180) : undefined;
}

function extensionFromFilename(filename) {
  if (!filename) return "";
  const m = filename.match(/(\.[A-Za-z0-9]{1,10})$/);
  return m ? m[1].toLowerCase() : "";
}

function guessContentType(headers) {
  const ct = getHeader(headers, "content-type");
  if (!ct) return "application/octet-stream";
  return String(ct).split(";")[0].trim() || "application/octet-stream";
}

function decodeBody(event) {
  const body = event?.body ?? "";
  if (body === null || body === undefined) return Buffer.alloc(0);
  if (Buffer.isBuffer(body)) return body;

  const isB64 = Boolean(event?.isBase64Encoded);
  const cte = String(getHeader(event?.headers, "content-transfer-encoding") || "").toLowerCase();
  const b64Header = cte === "base64";

  const asString = typeof body === "string" ? body : JSON.stringify(body);
  if (isB64 || b64Header) return Buffer.from(asString, "base64");
  return Buffer.from(asString, "utf8");
}

function json(statusCode, obj) {
  return {
    statusCode,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "OPTIONS,POST",
      "access-control-allow-headers":
        "content-type,content-length,content-disposition,content-transfer-encoding,x-filename",
    },
    body: JSON.stringify(obj),
  };
}

export async function handler(event) {
  try {
    if (event?.httpMethod === "OPTIONS") {
      return {
        statusCode: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "OPTIONS,POST",
          "access-control-allow-headers":
            "content-type,content-length,content-disposition,content-transfer-encoding,x-filename",
          "access-control-max-age": "600",
        },
        body: "",
      };
    }

    if (event?.httpMethod && event.httpMethod !== "POST") {
      return json(405, { error: "Method Not Allowed" });
    }

    const bucket = process.env.UPLOADS_BUCKET;
    if (!bucket) return json(500, { error: "Server misconfigured: missing UPLOADS_BUCKET" });

    const contentType = guessContentType(event?.headers);
    const bytes = decodeBody(event);
    if (!bytes.length) return json(400, { error: "Empty body" });

    const cd = getHeader(event?.headers, "content-disposition") || "";
    const m = String(cd).match(/filename\*?=(?:UTF-8''|")?([^\";]+)"?/i);
    const filenameHeader = sanitizeFilename(m ? decodeURIComponent(m[1]) : undefined);
    const xFilename = sanitizeFilename(getHeader(event?.headers, "x-filename"));
    const originalFilename = xFilename || filenameHeader;

    const ext = extensionFromFilename(originalFilename);
    const key = `uploads/${new Date().toISOString().slice(0, 10)}/${crypto.randomUUID()}${ext}`;

    await s3.send(
      new PutObjectCommand({
        Bucket: bucket,
        Key: key,
        Body: bytes,
        ContentType: contentType,
        Metadata: originalFilename ? { original_filename: originalFilename } : undefined,
      })
    );

    return json(201, { ok: true, bucket, key, bytes: bytes.length });
  } catch (err) {
    const message = err && typeof err === "object" && "message" in err ? String(err.message) : "Upload failed";
    return json(500, { error: message });
  }
}
