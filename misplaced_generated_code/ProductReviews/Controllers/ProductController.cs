using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ProductReviews.Data;
using ProductReviews.Models;

namespace ProductReviews.Controllers
{
    public class ProductController : Controller
    {
        private readonly AppDbContext _db;

        public ProductController(AppDbContext db)
        {
            _db = db;
        }

        // GET: /Product/Details/5
        public async Task<IActionResult> Details(int id)
        {
            var product = await _db.Products.FindAsync(id);
            if (product == null)
                return NotFound();

            var reviews = await _db.Reviews
                .Where(r => r.ProductId == id)
                .OrderByDescending(r => r.CreatedAt)
                .ToListAsync();

            var viewModel = new ProductReviewsViewModel
            {
                Product = product,
                Reviews = reviews
            };

            return View(viewModel);
        }

        // POST: /Product/SubmitReview
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> SubmitReview(int productId, string authorName, string content, int rating)
        {
            if (!ModelState.IsValid)
                return RedirectToAction("Details", new { id = productId });

            var product = await _db.Products.FindAsync(productId);
            if (product == null)
                return NotFound();

            var review = new Review
            {
                ProductId = productId,
                AuthorName = authorName,
                Content = content,
                Rating = Math.Clamp(rating, 1, 5),
                CreatedAt = DateTime.UtcNow
            };

            _db.Reviews.Add(review);
            await _db.SaveChangesAsync();

            return RedirectToAction("Details", new { id = productId });
        }
    }
}
