using Microsoft.EntityFrameworkCore;
using ProductReviewsMvc.Data;
using ProductReviewsMvc.Models;

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
