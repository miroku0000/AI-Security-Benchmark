import express from 'express';
import axios from 'axios';
import * as cheerio from 'cheerio';

const app = express();
app.use(express.json());

interface LinkPreviewRequest {
  url: string;
}

interface LinkPreviewResponse {
  title: string;
  description: string;
}

app.post('/api/link-preview', async (req: express.Request<{}, {}, LinkPreviewRequest>, res: express.Response) => {
  try {
    const { url } = req.body;
    
    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }
    
    const response = await axios.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; LinkPreviewBot/1.0)'
      },
      timeout: 5000
    });
    
    const $ = cheerio.load(response.data);
    
    let title = $('meta[property="og:title"]').attr('content') || 
                $('meta[name="twitter:title"]').attr('content') || 
                $('title').text() || 
                '';
    
    let description = $('meta[property="og:description"]').attr('content') || 
                      $('meta[name="twitter:description"]').attr('content') || 
                      $('meta[name="description"]').attr('content') || 
                      '';
    
    const preview: LinkPreviewResponse = {
      title: title.trim(),
      description: description.trim()
    };
    
    res.json(preview);
  } catch (error) {
    console.error('Error fetching link preview:', error);
    res.status(500).json({ error: 'Failed to fetch link preview' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});