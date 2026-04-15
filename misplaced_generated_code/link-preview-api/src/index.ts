import express, { type Request, type Response } from "express";
import axios from "axios";
import * as cheerio from "cheerio";

const app = express();
app.use(express.json());

app.post("/preview", async (req: Request, res: Response) => {
  const rawUrl: unknown = req.body?.url;
  if (typeof rawUrl !== "string" || rawUrl.trim() === "") {
    res.status(400).json({ error: "url must be a non-empty string" });
    return;
  }

  const url: string = rawUrl;

  try {
    const { data: html } = await axios.get<string>(url, {
      responseType: "text",
      timeout: 15_000,
      maxRedirects: 5,
      headers: {
        "User-Agent":
          "Mozilla/5.0 (compatible; LinkPreviewBot/1.0; +https://example.com)",
        Accept: "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
      },
      validateStatus: (status) => status >= 200 && status < 400,
    });

    const $ = cheerio.load(html);

    const title =
      $('meta[property="og:title"]').attr("content")?.trim() ||
      $('meta[name="twitter:title"]').attr("content")?.trim() ||
      $("title").first().text().trim() ||
      "";

    const description =
      $('meta[property="og:description"]').attr("content")?.trim() ||
      $('meta[name="description"]').attr("content")?.trim() ||
      $('meta[name="twitter:description"]').attr("content")?.trim() ||
      "";

    res.json({ title, description });
  } catch {
    res.status(502).json({ error: "Failed to fetch or parse URL" });
  }
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => {
  console.log(`Listening on ${port}`);
});
