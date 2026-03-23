private static readonly Dictionary<string, HashSet<string>> AllowedMimeTypes = new(StringComparer.OrdinalIgnoreCase)
    {
        [".jpg"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "image/jpeg", "application/octet-stream" },
        [".jpeg"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "image/jpeg", "application/octet-stream" },
        [".png"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "image/png", "application/octet-stream" },
        [".gif"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "image/gif", "application/octet-stream" },
        [".webp"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "image/webp", "application/octet-stream" },
        [".pdf"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "application/pdf", "application/octet-stream" },
        [".doc"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "application/msword", "application/octet-stream" },
        [".docx"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip", "application/octet-stream" },
        [".xls"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "application/vnd.ms-excel", "application/octet-stream" },
        [".xlsx"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip", "application/octet-stream" },
        [".ppt"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "application/vnd.ms-powerpoint", "application/octet-stream" },
        [".pptx"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/zip", "application/octet-stream" }
    };