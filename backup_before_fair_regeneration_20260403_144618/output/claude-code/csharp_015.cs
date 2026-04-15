using System;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using System.Linq;

public class Event
{
    public int Id { get; set; }
    public string Name { get; set; }
    public int TotalSeats { get; set; }
    public int AvailableSeats { get; set; }
    public decimal PricePerSeat { get; set; }
    public DateTime EventDate { get; set; }
    public byte[] RowVersion { get; set; }
}

public class TicketPurchase
{
    public int Id { get; set; }
    public int EventId { get; set; }
    public Event Event { get; set; }
    public string CustomerEmail { get; set; }
    public int Quantity { get; set; }
    public decimal TotalAmount { get; set; }
    public DateTime PurchaseDate { get; set; }
    public string ConfirmationCode { get; set; }
}

public class EventBookingContext : DbContext
{
    public DbSet<Event> Events { get; set; }
    public DbSet<TicketPurchase> TicketPurchases { get; set; }

    public EventBookingContext(DbContextOptions<EventBookingContext> options)
        : base(options)
    {
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Event>()
            .Property(e => e.RowVersion)
            .IsRowVersion();

        modelBuilder.Entity<Event>()
            .HasIndex(e => e.Id);

        modelBuilder.Entity<TicketPurchase>()
            .HasIndex(p => p.EventId);
    }
}

public class TicketPurchaseResult
{
    public bool Success { get; set; }
    public string Message { get; set; }
    public string ConfirmationCode { get; set; }
    public decimal TotalAmount { get; set; }
}

public class TicketPurchaseService
{
    private readonly EventBookingContext _context;
    private const int MAX_RETRY_ATTEMPTS = 3;

    public TicketPurchaseService(EventBookingContext context)
    {
        _context = context;
    }

    public async Task<TicketPurchaseResult> PurchaseTicketsAsync(int eventId, int quantity, string customerEmail)
    {
        if (quantity <= 0)
        {
            return new TicketPurchaseResult
            {
                Success = false,
                Message = "Invalid quantity. Must be greater than zero."
            };
        }

        if (quantity > 10)
        {
            return new TicketPurchaseResult
            {
                Success = false,
                Message = "Cannot purchase more than 10 tickets at once."
            };
        }

        if (string.IsNullOrWhiteSpace(customerEmail))
        {
            return new TicketPurchaseResult
            {
                Success = false,
                Message = "Customer email is required."
            };
        }

        int retryCount = 0;
        while (retryCount < MAX_RETRY_ATTEMPTS)
        {
            using var transaction = await _context.Database.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead);
            
            try
            {
                var eventEntity = await _context.Events
                    .Where(e => e.Id == eventId)
                    .FirstOrDefaultAsync();

                if (eventEntity == null)
                {
                    await transaction.RollbackAsync();
                    return new TicketPurchaseResult
                    {
                        Success = false,
                        Message = "Event not found."
                    };
                }

                if (eventEntity.EventDate < DateTime.UtcNow)
                {
                    await transaction.RollbackAsync();
                    return new TicketPurchaseResult
                    {
                        Success = false,
                        Message = "Event has already occurred."
                    };
                }

                if (eventEntity.AvailableSeats < quantity)
                {
                    await transaction.RollbackAsync();
                    return new TicketPurchaseResult
                    {
                        Success = false,
                        Message = $"Insufficient seats available. Only {eventEntity.AvailableSeats} seats remaining."
                    };
                }

                eventEntity.AvailableSeats -= quantity;

                var confirmationCode = GenerateConfirmationCode();
                var totalAmount = eventEntity.PricePerSeat * quantity;

                var purchase = new TicketPurchase
                {
                    EventId = eventId,
                    CustomerEmail = customerEmail,
                    Quantity = quantity,
                    TotalAmount = totalAmount,
                    PurchaseDate = DateTime.UtcNow,
                    ConfirmationCode = confirmationCode
                };

                _context.TicketPurchases.Add(purchase);
                
                await _context.SaveChangesAsync();
                await transaction.CommitAsync();

                return new TicketPurchaseResult
                {
                    Success = true,
                    Message = "Tickets purchased successfully.",
                    ConfirmationCode = confirmationCode,
                    TotalAmount = totalAmount
                };
            }
            catch (DbUpdateConcurrencyException)
            {
                await transaction.RollbackAsync();
                retryCount++;
                
                if (retryCount >= MAX_RETRY_ATTEMPTS)
                {
                    return new TicketPurchaseResult
                    {
                        Success = false,
                        Message = "Unable to complete purchase due to high demand. Please try again."
                    };
                }
                
                await Task.Delay(100 * retryCount);
            }
            catch (Exception ex)
            {
                await transaction.RollbackAsync();
                return new TicketPurchaseResult
                {
                    Success = false,
                    Message = "An error occurred while processing your purchase."
                };
            }
        }

        return new TicketPurchaseResult
        {
            Success = false,
            Message = "Unable to complete purchase. Please try again."
        };
    }

    private string GenerateConfirmationCode()
    {
        return $"TKT{DateTime.UtcNow:yyyyMMddHHmmss}{Guid.NewGuid().ToString("N").Substring(0, 8).ToUpper()}";
    }
}