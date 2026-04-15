using System.Net;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Html;

namespace ProductReviews.Helpers
{
    public static class ReviewFormatter
    {
        /// <summary>
        /// Safely formats user review content, allowing only bold and italic markup.
        /// Steps: HTML-encode everything first, then convert whitelisted markdown
        /// patterns (**bold** and *italic*) into their HTML equivalents.
        /// </summary>
        public static HtmlString FormatReview(string rawContent)
        {
            if (string.IsNullOrEmpty(rawContent))
                return new HtmlString(string.Empty);

            // Step 1: HTML-encode ALL user content to neutralize any injected HTML/scripts
            string encoded = WebUtility.HtmlEncode(rawContent);

            // Step 2: Convert newlines to <br> tags
            encoded = encoded.Replace("\r\n", "<br>").Replace("\n", "<br>");

            // Step 3: Convert whitelisted markdown-style formatting to safe HTML
            // Bold: **text** -> <strong>text</strong> (must process before italic)
            encoded = Regex.Replace(encoded, @"\*\*(.+?)\*\*", "<strong>$1</strong>");

            // Italic: *text* -> <em>text</em>
            encoded = Regex.Replace(encoded, @"\*(.+?)\*", "<em>$1</em>");

            return new HtmlString(encoded);
        }
    }
}
