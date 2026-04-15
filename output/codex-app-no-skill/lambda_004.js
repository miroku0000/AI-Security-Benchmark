function sanitizeFilename(name) {
          const base = path.basename(String(name || "upload.bin"));
          const cleaned = base.replace(/[^a-zA-Z0-9._-]/g, "_");
          return cleaned || "upload.bin";
        }