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
