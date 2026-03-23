using System.Text.RegularExpressions;

namespace ProductReviewsMvc.Services;

public static class ReviewHtmlSanitizer
{
    private static readonly Regex StripDisallowedTags = new(
        @"<(?!\/?(?:b|strong|i|em|u|br|p)\b)[^>]+>",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static string Sanitize(string? html)
    {
        if (string.IsNullOrWhiteSpace(html)) return string.Empty;
        var s = Regex.Replace(html, @"<script[\s\S]*?</script>", string.Empty, RegexOptions.IgnoreCase);
        s = Regex.Replace(s, @"on\w+\s*=\s*""[^""]*""", string.Empty, RegexOptions.IgnoreCase);
        s = Regex.Replace(s, @"on\w+\s*=\s*'[^']*'", string.Empty, RegexOptions.IgnoreCase);
        return StripDisallowedTags.Replace(s, string.Empty);
    }
}
