var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection")));

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await AppDbInitializer.SeedAsync(db);
}

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Products}/{action=Details}/{id?}");

await app.RunAsync();

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

Data/AppDbContext.cs
using Microsoft.EntityFrameworkCore;
using ProductReviewsMvc.Models;

namespace ProductReviewsMvc.Data;

public sealed class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
    {
    }

    public DbSet<Product> Products => Set<Product>();
    public DbSet<Review> Reviews => Set<Review>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Product>(entity =>
        {
            entity.HasKey(x => x.Id);
            entity.Property(x => x.Name).HasMaxLength(200).IsRequired();
        });

        modelBuilder.Entity<Review>(entity =>
        {
            entity.HasKey(x => x.Id);
            entity.Property(x => x.AuthorName).HasMaxLength(100).IsRequired();
            entity.Property(x => x.Content).HasMaxLength(4000).IsRequired();
            entity.HasIndex(x => x.ProductId);
            entity.HasOne(x => x.Product)
                .WithMany(x => x.Reviews)
                .HasForeignKey(x => x.ProductId)
                .OnDelete(DeleteBehavior.Cascade);
        });
    }
}

Data/AppDbInitializer.cs
using Microsoft.EntityFrameworkCore;
using ProductReviewsMvc.Models;

namespace ProductReviewsMvc.Data;

public static class AppDbInitializer
{
    public static async Task SeedAsync(AppDbContext db)
    {
        await db.Database.EnsureCreatedAsync();

        if (await db.Products.AnyAsync())
        {
            return;
        }

        var product = new Product
        {
            Name = "Noise-Cancelling Headphones"
        };

        db.Products.Add(product);
        await db.SaveChangesAsync();

        db.Reviews.AddRange(
            new Review
            {
                ProductId = product.Id,
                AuthorName = "Avery",
                Content = "Great sound quality and **excellent** battery life.",
                CreatedUtc = DateTime.UtcNow.AddDays(-3)
            },
            new Review
            {
                ProductId = product.Id,
                AuthorName = "Jordan",
                Content = "Very comfortable for long sessions and *surprisingly* light.",
                CreatedUtc = DateTime.UtcNow.AddDays(-2)
            },
            new Review
            {
                ProductId = product.Id,
                AuthorName = "Taylor",
                Content = "The ANC is **strong** and the ear cups feel *premium*.",
                CreatedUtc = DateTime.UtcNow.AddDays(-1)
            });

        await db.SaveChangesAsync();
    }
}

Models/Product.cs
using System.ComponentModel.DataAnnotations;

namespace ProductReviewsMvc.Models;

public sealed class Product
{
    public int Id { get; set; }

    [Required]
    [StringLength(200)]
    public string Name { get; set; } = string.Empty;

    public List<Review> Reviews { get; set; } = new();
}

Models/Review.cs
using System.ComponentModel.DataAnnotations;

namespace ProductReviewsMvc.Models;

public sealed class Review
{
    public int Id { get; set; }

    [Required]
    public int ProductId { get; set; }

    [Required]
    [StringLength(100)]
    public string AuthorName { get; set; } = string.Empty;

    [Required]
    [StringLength(4000)]
    public string Content { get; set; } = string.Empty;

    public DateTime CreatedUtc { get; set; }

    public Product? Product { get; set; }
}

Services/ReviewFormatter.cs
using System.Text.Encodings.Web;
using System.Text.RegularExpressions;

namespace ProductReviewsMvc.Services;

public static partial class ReviewFormatter
{
    [GeneratedRegex(@"\*\*(.+?)\*\*", RegexOptions.Singleline)]
    private static partial Regex BoldRegex();

    [GeneratedRegex(@"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", RegexOptions.Singleline)]
    private static partial Regex ItalicRegex();

    public static string ToSafeHtml(string? input)
    {
        if (string.IsNullOrWhiteSpace(input))
        {
            return string.Empty;
        }

        var encoded = HtmlEncoder.Default.Encode(input)
            .Replace("\r\n", "\n", StringComparison.Ordinal)
            .Replace("\r", "\n", StringComparison.Ordinal);

        encoded = BoldRegex().Replace(encoded, "<strong>$1</strong>");
        encoded = ItalicRegex().Replace(encoded, "<em>$1</em>");

        return encoded.Replace("\n", "<br />", StringComparison.Ordinal);
    }
}

ViewModels/ProductDetailsViewModel.cs
namespace ProductReviewsMvc.ViewModels;

public sealed class ProductDetailsViewModel
{
    public int ProductId { get; set; }
    public string ProductName { get; set; } = string.Empty;
    public IReadOnlyList<ReviewViewModel> Reviews { get; set; } = Array.Empty<ReviewViewModel>();
}

public sealed class ReviewViewModel
{
    public string AuthorName { get; set; } = string.Empty;
    public string FormattedContent { get; set; } = string.Empty;
    public DateTime CreatedUtc { get; set; }
}

Controllers/ProductsController.cs
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ProductReviewsMvc.Data;
using ProductReviewsMvc.Services;
using ProductReviewsMvc.ViewModels;

namespace ProductReviewsMvc.Controllers;

public sealed class ProductsController : Controller
{
    private readonly AppDbContext _db;

    public ProductsController(AppDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<IActionResult> Details(int id = 1, CancellationToken cancellationToken = default)
    {
        var product = await _db.Products
            .AsNoTracking()
            .SingleOrDefaultAsync(x => x.Id == id, cancellationToken);

        if (product is null)
        {
            return NotFound();
        }

        var reviews = await _db.Reviews
            .AsNoTracking()
            .Where(x => x.ProductId == id)
            .OrderByDescending(x => x.CreatedUtc)
            .ToListAsync(cancellationToken);

        var model = new ProductDetailsViewModel
        {
            ProductId = product.Id,
            ProductName = product.Name,
            Reviews = reviews.Select(x => new ReviewViewModel
            {
                AuthorName = x.AuthorName,
                FormattedContent = ReviewFormatter.ToSafeHtml(x.Content),
                CreatedUtc = x.CreatedUtc
            }).ToList()
        };

        return View(model);
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
        body {
            font-family: system-ui, sans-serif;
            margin: 2rem;
            line-height: 1.5;
            color: #1f2937;
            background: #f9fafb;
        }

        .page {
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
        }

        .review {
            border-top: 1px solid #e5e7eb;
            padding: 1rem 0;
        }

        .review:first-of-type {
            border-top: 0;
            padding-top: 0;
        }

        .meta {
            color: #6b7280;
            font-size: 0.95rem;
            margin-bottom: 0.5rem;
        }

        .body {
            white-space: normal;
        }

        .hint {
            color: #4b5563;
            font-size: 0.95rem;
            background: #f3f4f6;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 1.5rem;
        }
    </style>
</head>
<body>
    <main class="page">
        @RenderBody()
    </main>
</body>
</html>

Views/Products/Details.cshtml
@model ProductReviewsMvc.ViewModels.ProductDetailsViewModel

@{
    ViewData["Title"] = $"{Model.ProductName} Reviews";
}

<h1>@Model.ProductName</h1>
<p class="hint">Reviews support basic formatting using **bold** and *italic*.</p>

<h2>Customer Reviews</h2>

@if (Model.Reviews.Count == 0)
{
    <p>No reviews yet.</p>
}
else
{
    @foreach (var review in Model.Reviews)
    {
        <article class="review">
            <div class="meta">
                <strong>@review.AuthorName</strong>
                &middot;
                @review.CreatedUtc.ToLocalTime().ToString("MMM d, yyyy h:mm tt")
            </div>
            <div class="body">@Html.Raw(review.FormattedContent)</div>
        </article>
    }
}