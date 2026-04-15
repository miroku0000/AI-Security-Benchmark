using System;
using System.ComponentModel.DataAnnotations;

namespace ProductReviews.Models
{
    public class Review
    {
        public int Id { get; set; }

        public int ProductId { get; set; }

        [Required]
        [StringLength(100)]
        public string AuthorName { get; set; }

        [Required]
        [StringLength(5000)]
        public string Content { get; set; }

        [Range(1, 5)]
        public int Rating { get; set; }

        public DateTime CreatedAt { get; set; }
    }

    public class Product
    {
        public int Id { get; set; }

        [Required]
        [StringLength(200)]
        public string Name { get; set; }

        [StringLength(2000)]
        public string Description { get; set; }

        public decimal Price { get; set; }
    }

    public class ProductReviewsViewModel
    {
        public Product Product { get; set; }
        public List<Review> Reviews { get; set; }
    }
}
