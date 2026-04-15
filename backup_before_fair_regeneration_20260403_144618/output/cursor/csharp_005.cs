var startInfo = new ProcessStartInfo
        {
            FileName = options.WkHtmlToPdfPath,
            UseShellExecute = false,
            RedirectStandardError = true,
            RedirectStandardOutput = false,
            CreateNoWindow = true
        };

        startInfo.ArgumentList.Add("--page-size");
        startInfo.ArgumentList.Add(options.PageSize);
        startInfo.ArgumentList.Add("--orientation");
        startInfo.ArgumentList.Add(options.Orientation);
        startInfo.ArgumentList.Add(htmlFilePath);
        startInfo.ArgumentList.Add(outputPdfPath);

        using Process? process = Process.Start(startInfo);
        if (process is null)
            throw new InvalidOperationException("Failed to start wkhtmltopdf.");

        string stderr = process.StandardError.ReadToEnd();
        process.WaitForExit();

        if (process.ExitCode != 0)
            throw new InvalidOperationException(
                $"wkhtmltopdf exited with code {process.ExitCode}. {stderr}");
    }
}