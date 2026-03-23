using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.Data.Entity;

namespace ProductReviews.Controllers
{
    public class ReviewController : Controller
    {
        private ApplicationDbContext db = new ApplicationDbContext();

        public ActionResult Index(int productId)
        {
            var reviews = db.Reviews
                .Where(r => r.ProductId == productId)
                .OrderByDescending(r => r.CreatedDate)
                .ToList();

            ViewBag.ProductId = productId;
            var product = db.Products.Find(productId);
            ViewBag.ProductName = product?.Name ?? "Product";

            return View(reviews);
        }

        [HttpGet]
        public ActionResult Create(int productId)
        {
            var review = new Review { ProductId = productId };
            return View(review);
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public ActionResult Create(Review review)
        {
            if (ModelState.IsValid)
            {
                review.CreatedDate = DateTime.Now;
                review.UserId = User.Identity.Name;
                db.Reviews.Add(review);
                db.SaveChanges();
                return RedirectToAction("Index", new { productId = review.ProductId });
            }

            return View(review);
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                db.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}

public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext() : base("DefaultConnection")
    {
    }

    public DbSet<Review> Reviews { get; set; }
    public DbSet<Product> Products { get; set; }
}

public class Review
{
    public int Id { get; set; }
    public int ProductId { get; set; }
    public string UserId { get; set; }
    public string UserName { get; set; }
    public int Rating { get; set; }
    public string Title { get; set; }
    public string Content { get; set; }
    public DateTime CreatedDate { get; set; }
    public virtual Product Product { get; set; }
}

public class Product
{
    public int Id { get; set; }
    public string Name { get; set; }
    public string Description { get; set; }
    public decimal Price { get; set; }
    public virtual ICollection<Review> Reviews { get; set; }
}