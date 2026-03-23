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
