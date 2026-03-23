using System;
using System.Diagnostics;
using System.IO;
using System.Text;

public class PdfGenerator
{
    public enum PageSize
    {
        A4,
        A3,
        Letter,
        Legal,
        A5,
        B5,
        Executive
    }

    public enum Orientation
    {
        Portrait,
        Landscape
    }

    public class PdfOptions
    {
        public PageSize PageSize { get; set; } = PageSize.A4;
        public Orientation Orientation { get; set; } = Orientation.Portrait;
        public string MarginTop { get; set; } = "10mm";
        public string MarginBottom { get; set; } = "10mm";
        public string MarginLeft { get; set; } = "10mm";
        public string MarginRight { get; set; } = "10mm";
        public bool Grayscale { get; set; } = false;
        public bool LowQuality { get; set; } = false;
        public int? Dpi { get; set; } = null;
        public string PageOffset { get; set; } = "0";
        public int? Copies { get; set; } = null;
        public bool EnableJavaScript { get; set; } = true;
        public bool NoBackground { get; set; } = false;
        public string Title { get; set; } = null;
        public string Encoding { get; set; } = "utf-8";
        public bool DisableSmartShrinking { get; set; } = false;
        public string CustomArgs { get; set; } = null;
    }

    public static bool GeneratePdfFromHtml(string htmlFilePath, string outputPdfPath, PdfOptions options = null)
    {
        if (string.IsNullOrWhiteSpace(htmlFilePath))
            throw new ArgumentException("HTML file path cannot be null or empty.", nameof(htmlFilePath));
        
        if (string.IsNullOrWhiteSpace(outputPdfPath))
            throw new ArgumentException("Output PDF path cannot be null or empty.", nameof(outputPdfPath));
        
        if (!File.Exists(htmlFilePath))
            throw new FileNotFoundException("HTML file not found.", htmlFilePath);

        string outputDir = Path.GetDirectoryName(outputPdfPath);
        if (!string.IsNullOrEmpty(outputDir) && !Directory.Exists(outputDir))
            Directory.CreateDirectory(outputDir);

        if (options == null)
            options = new PdfOptions();

        string arguments = BuildCommandArguments(htmlFilePath, outputPdfPath, options);

        try
        {
            using (Process process = new Process())
            {
                process.StartInfo.FileName = "wkhtmltopdf";
                process.StartInfo.Arguments = arguments;
                process.StartInfo.UseShellExecute = false;
                process.StartInfo.RedirectStandardOutput = true;
                process.StartInfo.RedirectStandardError = true;
                process.StartInfo.CreateNoWindow = true;

                process.Start();
                
                string output = process.StandardOutput.ReadToEnd();
                string error = process.StandardError.ReadToEnd();
                
                process.WaitForExit();

                if (process.ExitCode != 0)
                {
                    Console.WriteLine($"Error: {error}");
                    return false;
                }

                return File.Exists(outputPdfPath);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Exception occurred: {ex.Message}");
            return false;
        }
    }

    private static string BuildCommandArguments(string htmlFilePath, string outputPdfPath, PdfOptions options)
    {
        StringBuilder args = new StringBuilder();

        args.Append($"--page-size {options.PageSize} ");
        args.Append($"--orientation {options.Orientation} ");
        args.Append($"--margin-top {options.MarginTop} ");
        args.Append($"--margin-bottom {options.MarginBottom} ");
        args.Append($"--margin-left {options.MarginLeft} ");
        args.Append($"--margin-right {options.MarginRight} ");
        args.Append($"--encoding {options.Encoding} ");
        args.Append($"--page-offset {options.PageOffset} ");

        if (options.Grayscale)
            args.Append("--grayscale ");

        if (options.LowQuality)
            args.Append("--lowquality ");

        if (options.NoBackground)
            args.Append("--no-background ");

        if (options.DisableSmartShrinking)
            args.Append("--disable-smart-shrinking ");

        if (!options.EnableJavaScript)
            args.Append("--disable-javascript ");

        if (options.Dpi.HasValue)
            args.Append($"--dpi {options.Dpi.Value} ");

        if (options.Copies.HasValue)
            args.Append($"--copies {options.Copies.Value} ");

        if (!string.IsNullOrWhiteSpace(options.Title))
            args.Append($"--title \"{options.Title}\" ");

        if (!string.IsNullOrWhiteSpace(options.CustomArgs))
            args.Append($"{options.CustomArgs} ");

        args.Append($"\"{htmlFilePath}\" \"{outputPdfPath}\"");

        return args.ToString();
    }

    public static bool GeneratePdfFromHtmlString(string htmlContent, string outputPdfPath, PdfOptions options = null)
    {
        if (string.IsNullOrWhiteSpace(htmlContent))
            throw new ArgumentException("HTML content cannot be null or empty.", nameof(htmlContent));

        string tempHtmlFile = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid()}.html");
        
        try
        {
            File.WriteAllText(tempHtmlFile, htmlContent, Encoding.UTF8);
            return GeneratePdfFromHtml(tempHtmlFile, outputPdfPath, options);
        }
        finally
        {
            if (File.Exists(tempHtmlFile))
                File.Delete(tempHtmlFile);
        }
    }

    public static void Main(string[] args)
    {
        string htmlPath = @"C:\temp\input.html";
        string pdfPath = @"C:\temp\output.pdf";
        
        PdfOptions options = new PdfOptions
        {
            PageSize = PageSize.A4,
            Orientation = Orientation.Portrait,
            MarginTop = "15mm",
            MarginBottom = "15mm",
            MarginLeft = "10mm",
            MarginRight = "10mm",
            EnableJavaScript = true,
            Title = "Generated PDF Report"
        };

        bool success = GeneratePdfFromHtml(htmlPath, pdfPath, options);
        
        if (success)
            Console.WriteLine($"PDF generated successfully: {pdfPath}");
        else
            Console.WriteLine("Failed to generate PDF");
    }
}