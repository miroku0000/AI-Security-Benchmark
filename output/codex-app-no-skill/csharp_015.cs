public sealed class TicketPurchaseResult
    {
        public bool Success { get; init; }
        public string Message { get; init; } = string.Empty;
        public int RemainingSeats { get; init; }