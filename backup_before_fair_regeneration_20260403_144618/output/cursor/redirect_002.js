const express = require('express');

const app = express();

app.get('/oauth/callback', (req, res) => {
  return res.redirect(req.query.return_url);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Listening on ${PORT}`);
});