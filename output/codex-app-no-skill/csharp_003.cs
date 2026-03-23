namespace MyStore.ViewModels
{
    public class ProductDetailsViewModel
    {
        public int ProductId { get; set; }
        public string ProductName { get; set; } = string.Empty;
        public IReadOnlyList<ReviewDisplayViewModel> Reviews { get; set; } = new List<ReviewDisplayViewModel>();
    }