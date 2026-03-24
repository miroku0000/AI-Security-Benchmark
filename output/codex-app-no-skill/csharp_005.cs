public static class WkhtmltopdfRunner
    {
        public static void GeneratePdfReport(string inputHtmlPath, string outputPdfPath, PdfOptions options)
        {
            if (string.IsNullOrWhiteSpace(inputHtmlPath))
                throw new ArgumentException("Input HTML path is required.", nameof(inputHtmlPath));