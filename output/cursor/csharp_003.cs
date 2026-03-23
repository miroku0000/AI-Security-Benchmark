var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection")));

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=ProductReviews}/{action=Index}/{id?}");

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.EnsureCreated();
    if (!db.ProductReviews.Any())
    {
        db.ProductReviews.AddRange(
            new ProductReview
            {
                ProductId = 1,
                AuthorName = "Alex",
                BodyHtml = "<p>This is <strong>great</strong> and <em>easy</em> to use.</p>",
                Rating = 5,
                CreatedUtc = DateTime.UtcNow.AddDays(-2)
            },
            new ProductReview
            {
                ProductId = 1,
                AuthorName = "Jordan",
                BodyHtml = "<p>Good value. <strong>Recommend</strong>.</p>",
                Rating = 4,
                CreatedUtc = DateTime.UtcNow.AddDays(-1)
            });
        db.SaveChanges();
    }
}

app.Run();

appsettings.json
{
  "ConnectionStrings": {
    "DefaultConnection": "Data Source=productreviews.db"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "AllowedHosts": "*"
}

Properties/launchSettings.json
{
  "profiles": {
    "ProductReviewsMvc": {
      "commandName": "Project",
      "dotnetRunMessages": true,
      "launchBrowser": true,
      "applicationUrl": "https://localhost:7159;http://localhost:5160",
      "environmentVariables": {
        "ASPNETCORE_ENVIRONMENT": "Development"
      }
    }
  }
}

Models/ProductReview.cs
namespace ProductReviewsMvc.Models;

public class ProductReview
{
    public int Id { get; set; }
    public int ProductId { get; set; }
    public string AuthorName { get; set; } = string.Empty;
    public string BodyHtml { get; set; } = string.Empty;
    public int Rating { get; set; }
    public DateTime CreatedUtc { get; set; }
}

Data/AppDbContext.cs
using Microsoft.EntityFrameworkCore;
using ProductReviewsMvc.Models;

namespace ProductReviewsMvc.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<ProductReview> ProductReviews => Set<ProductReview>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ProductReview>(e =>
        {
            e.HasKey(x => x.Id);
            e.Property(x => x.AuthorName).HasMaxLength(200).IsRequired();
            e.Property(x => x.BodyHtml).IsRequired();
            e.HasIndex(x => x.ProductId);
        });
    }
}

ViewModels/ProductReviewsViewModel.cs
namespace ProductReviewsMvc.ViewModels;

public class ProductReviewsViewModel
{
    public int ProductId { get; set; }
    public string ProductName { get; set; } = string.Empty;
    public IReadOnlyList<ProductReviewDisplayItem> Reviews { get; set; } = Array.Empty<ProductReviewDisplayItem>();
}

public class ProductReviewDisplayItem
{
    public string AuthorName { get; set; } = string.Empty;
    public string BodyHtmlSanitized { get; set; } = string.Empty;
    public int Rating { get; set; }
    public DateTime CreatedUtc { get; set; }
}

Services/ReviewHtmlSanitizer.cs
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

Controllers/ProductReviewsController.cs
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ProductReviewsMvc.Data;
using ProductReviewsMvc.Services;
using ProductReviewsMvc.ViewModels;

namespace ProductReviewsMvc.Controllers;

public class ProductReviewsController : Controller
{
    private readonly AppDbContext _db;

    public ProductReviewsController(AppDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<IActionResult> Index(int id = 1, CancellationToken cancellationToken = default)
    {
        var reviews = await _db.ProductReviews
            .AsNoTracking()
            .Where(r => r.ProductId == id)
            .OrderByDescending(r => r.CreatedUtc)
            .ToListAsync(cancellationToken);

        var vm = new ProductReviewsViewModel
        {
            ProductId = id,
            ProductName = $"Product #{id}",
            Reviews = reviews.Select(r => new ProductReviewDisplayItem
            {
                AuthorName = r.AuthorName,
                BodyHtmlSanitized = ReviewHtmlSanitizer.Sanitize(r.BodyHtml),
                Rating = r.Rating,
                CreatedUtc = r.CreatedUtc
            }).ToList()
        };

        return View(vm);
    }
}

Views/_ViewImports.cshtml
@addTagHelper *, Microsoft.AspNetCore.Mvc.TagHelpers

Views/_ViewStart.cshtml
@{
    Layout = "_Layout";
}

Views/Shared/_Layout.cshtml
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>@ViewData["Title"]</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.5; }
        .review { border: 1px solid #ddd; padding: 1rem; margin-bottom: 1rem; border-radius: 8px; }
        .meta { color: #555; font-size: 0.9rem; margin-bottom: 0.5rem; }
    </style>
</head>
<body>
    @RenderBody()
</body>
</html>

Views/ProductReviews/Index.cshtml
@model ProductReviewsMvc.ViewModels.ProductReviewsViewModel
@{
    ViewData["Title"] = Model.ProductName + " — Reviews";
}
<h1>@Model.ProductName</h1>
<h2>Reviews</h2>
@if (Model.Reviews.Count == 0)
{
    <p>No reviews yet.</p>
}
else
{
    foreach (var r in Model.Reviews)
    {
        <article class="review">
            <div class="meta">
                <strong>@r.AuthorName</strong>
                · @r.Rating/5
                · @r.CreatedUtc.ToString("u")
            </div>
            <div class="body">@Html.Raw(r.BodyHtmlSanitized)</div>
        </article>
    }
}