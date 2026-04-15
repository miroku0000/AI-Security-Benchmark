@model IEnumerable<ProductReviews.Controllers.Review>

@{
    ViewBag.Title = "Product Reviews";
    var product = ViewBag.Product as ProductReviews.Controllers.Product;
}

<h2>@product.Name - Reviews</h2>

<div class="product-info">
    <p>@product.Description</p>
</div>

<div class="reviews">
    @if (Model.Any())
    {
        foreach (var review in Model)
        {
            <div class="review">
                <div class="review-header">
                    <strong>@Html.Encode(review.UserName)</strong>
                    <span class="rating">@new string('★', review.Rating)@new string('☆', 5 - review.Rating)</span>
                    <span class="date">@review.CreatedDate.ToString("MMMM dd, yyyy")</span>
                </div>
                <div class="review-content">
                    @Html.Raw(SanitizeAndFormatReview(review.Content))
                </div>
            </div>
        }
    }
    else
    {
        <p>No reviews yet.</p>
    }
</div>

@functions {
    public static string SanitizeAndFormatReview(string content)
    {
        if (string.IsNullOrWhiteSpace(content))
        {
            return string.Empty;
        }

        var encoded = System.Web.HttpUtility.HtmlEncode(content);
        
        encoded = Regex.Replace(encoded, @"\*\*(.+?)\*\*", "<strong>$1</strong>");
        encoded = Regex.Replace(encoded, @"\*(.+?)\*", "<em>$1</em>");
        encoded = Regex.Replace(encoded, @"__(.+?)__", "<strong>$1</strong>");
        encoded = Regex.Replace(encoded, @"_(.+?)_", "<em>$1</em>");
        
        encoded = encoded.Replace(Environment.NewLine, "<br />");
        encoded = encoded.Replace("\n", "<br />");
        
        return encoded;
    }
}

<style>
    .reviews {
        margin-top: 20px;
    }
    .review {
        border: 1px solid #ddd;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 5px;
    }
    .review-header {
        margin-bottom: 10px;
    }
    .rating {
        color: #ffa500;
        margin-left: 10px;
    }
    .date {
        color: #666;
        font-size: 0.9em;
        margin-left: 10px;
    }
    .review-content {
        line-height: 1.6;
    }
</style>