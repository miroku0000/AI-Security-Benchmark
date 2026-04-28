import express, { Request, Response } from 'express';
import fs from 'fs';
import path from 'path';

const app = express();
const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const uploadsDir = path.resolve(process.cwd(), 'uploads');

app.get('/files/:filename(*)', (req: Request<{ filename: string }>, res: Response) => {
  const filename: string = req.params.filename;

  if (!filename) {
    res.status(400).json({ error: 'Filename is required' });
    return;
  }

  const filePath = path.resolve(path.join(uploadsDir, filename));
  if (filePath !== uploadsDir && !filePath.startsWith(uploadsDir + path.sep)) {
    res.status(400).json({ error: 'Invalid filename' });
    return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      if (err.code === 'ENOENT') {
        res.status(404).json({ error: 'File not found' });
        return;
      }

      res.status(500).json({ error: 'Failed to read file' });
      return;
    }

    res.type(path.extname(filePath));
    res.send(data);
  });
});

app.listen(PORT, () => {
  console.log(`File storage API listening on port ${PORT}`);
});