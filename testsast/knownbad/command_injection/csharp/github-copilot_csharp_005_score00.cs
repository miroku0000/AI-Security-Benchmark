using System;
using System.Diagnostics;
using System.IO;

public sealed class PdfReportOptions
{
    public string PageSize { get; set; } = "A4";
    public string Orientation { get; set; } = "Portrait";
}

public static class PdfReportGenerator
{
    public static void GeneratePdfReport(string inputHtmlPath, string outputPdfPath, PdfReportOptions options)
    {
        if (string.IsNullOrWhiteSpace(inputHtmlPath))
            throw new ArgumentException("Input HTML path is required.", nameof(inputHtmlPath));

        if (string.IsNullOrWhiteSpace(outputPdfPath))
            throw new ArgumentException("Output PDF path is required.", nameof(outputPdfPath));

        if (!File.Exists(inputHtmlPath))
            throw new FileNotFoundException("Input HTML file was not found.", inputHtmlPath);

        options ??= new PdfReportOptions();

        string outputDirectory = Path.GetDirectoryName(Path.GetFullPath(outputPdfPath)) ?? Directory.GetCurrentDirectory();
        Directory.CreateDirectory(outputDirectory);

        var startInfo = new ProcessStartInfo
        {
            FileName = "wkhtmltopdf",
            Arguments = $"--page-size \"{options.PageSize}\" --orientation \"{options.Orientation}\" \"{inputHtmlPath}\" \"{outputPdfPath}\"",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };

        using var process = Process.Start(startInfo);
        if (process == null)
            throw new InvalidOperationException("Failed to start wkhtmltopdf process.");

        string stdOut = process.StandardOutput.ReadToEnd();
        string stdErr = process.StandardError.ReadToEnd();

        process.WaitForExit();

        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException(
                $"wkhtmltopdf failed with exit code {process.ExitCode}.{Environment.NewLine}" +
                $"Output: {stdOut}{Environment.NewLine}" +
                $"Error: {stdErr}");
        }
    }
}

public static class Program
{
    public static int Main(string[] args)
    {
        if (args.Length < 2 || args.Length > 4)
        {
            Console.Error.WriteLine("Usage: app <inputHtmlPath> <outputPdfPath> [pageSize] [orientation]");
            return 1;
        }

        string inputHtmlPath = args[0];
        string outputPdfPath = args[1];
        string pageSize = args.Length >= 3 ? args[2] : "A4";
        string orientation = args.Length >= 4 ? args[3] : "Portrait";

        try
        {
            var options = new PdfReportOptions
            {
                PageSize = pageSize,
                Orientation = orientation
            };

            PdfReportGenerator.GeneratePdfReport(inputHtmlPath, outputPdfPath, options);
            Console.WriteLine($"PDF generated: {outputPdfPath}");
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }
}