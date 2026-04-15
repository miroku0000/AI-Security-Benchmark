app.post('/notify', async (req, res) => {
  try {
    const result = await sendEmailNotification(req.body);
    res.status(200).json({
      success: true,
      result,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.response && error.response.body ? error.response.body : error.message,
    });
  }
});