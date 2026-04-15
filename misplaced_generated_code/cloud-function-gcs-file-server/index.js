"use strict";

const functions = require("@google-cloud/functions-framework");
const { Storage } = require("@google-cloud/storage");

const storage = new Storage();

functions.http("serveFile", async (req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, HEAD");
    res.status(405).send("Method Not Allowed");
    return;
  }

  const bucketName = Array.isArray(req.query.bucket)
    ? req.query.bucket[0]
    : req.query.bucket;
  const filePath = Array.isArray(req.query.path)
    ? req.query.path[0]
    : req.query.path;

  if (
    !bucketName ||
    typeof bucketName !== "string" ||
    !filePath ||
    typeof filePath !== "string"
  ) {
    res.status(400).send("Missing bucket or path query parameter");
    return;
  }

  const normalizedPath = filePath.replace(/^\/+/, "");
  if (!normalizedPath || normalizedPath.includes("..")) {
    res.status(400).send("Invalid path");
    return;
  }

  const bucket = storage.bucket(bucketName);
  const file = bucket.file(normalizedPath);

  try {
    const [exists] = await file.exists();
    if (!exists) {
      res.status(404).send("Not Found");
      return;
    }

    const [metadata] = await file.getMetadata();

    if (metadata.contentType) {
      res.setHeader("Content-Type", metadata.contentType);
    }
    if (metadata.size != null) {
      res.setHeader("Content-Length", String(metadata.size));
    }
    if (metadata.cacheControl) {
      res.setHeader("Cache-Control", metadata.cacheControl);
    }
    if (metadata.contentDisposition) {
      res.setHeader("Content-Disposition", metadata.contentDisposition);
    }

    if (req.method === "HEAD") {
      res.status(200).end();
      return;
    }

    const readStream = file.createReadStream();

    readStream.on("error", () => {
      if (!res.headersSent) {
        res.status(500).send("Error streaming file");
      } else {
        res.destroy();
      }
    });

    readStream.pipe(res);
  } catch (err) {
    if (!res.headersSent) {
      res.status(500).send("Internal Server Error");
    }
  }
});
