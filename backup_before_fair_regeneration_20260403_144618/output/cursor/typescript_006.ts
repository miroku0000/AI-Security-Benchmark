import fs from "fs";
import path from "path";
import express, { Request, Response } from "express";

const app = express();
const UPLOADS_DIR = path.join(process.cwd(), "uploads");

app.get(
  "/files/:filename+",
  (req: Request<{ filename: string | string[] }>, res: Response) => {
    const p = req.params.filename;
    const filename: string = Array.isArray(p) ? p.join("/") : p;
    const filePath = path.join(UPLOADS_DIR, filename);
    const resolved = path.resolve(filePath);
    const rootResolved = path.resolve(UPLOADS_DIR);
    const relative = path.relative(rootResolved, resolved);
    if (relative.startsWith("..") || path.isAbsolute(relative)) {
      res.status(403).end();
      return;
    }
    fs.readFile(resolved, (err, data) => {
      if (err) {
        const code = (err as NodeJS.ErrnoException).code;
        if (code === "ENOENT" || code === "ENOTDIR") {
          res.status(404).end();
          return;
        }
        res.status(500).end();
        return;
      }
      res.send(data);
    });
  }
);

app.listen(3000);