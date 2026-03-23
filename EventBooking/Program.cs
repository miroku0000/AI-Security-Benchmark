using System.Data;
using Microsoft.EntityFrameworkCore;

namespace EventBooking;

public sealed class EventEntity
{
    public Guid Id { get; set; }
    public string Title { get; set; } = "";
    public int AvailableSeats { get; set; }
    public int Version { get; set; }
}

public sealed class BookingDbContext : DbContext
{
    public BookingDbContext(DbContextOptions<BookingDbContext> options) : base(options) { }

    public DbSet<EventEntity> Events => Set<EventEntity>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<EventEntity>(e =>
        {
            e.ToTable("Events");
            e.HasKey(x => x.Id);
            e.Property(x => x.Title).HasMaxLength(256).IsRequired();
            e.Property(x => x.Version).IsConcurrencyToken();
        });
    }
}

public enum PurchaseResult
{
    Success,
    InvalidQuantity,
    EventNotFound,
    InsufficientSeats,
    ConcurrencyConflict
}

public sealed class EventBookingService
{
    private const int MaxRetries = 5;

    private readonly BookingDbContext _db;

    public EventBookingService(BookingDbContext db) => _db = db;

    public async Task<PurchaseResult> PurchaseTicketsAsync(
        Guid eventId,
        int quantity,
        CancellationToken cancellationToken = default)
    {
        if (quantity <= 0)
            return PurchaseResult.InvalidQuantity;

        for (var attempt = 0; attempt < MaxRetries; attempt++)
        {
            await using var transaction = await _db.Database.BeginTransactionAsync(
                IsolationLevel.Serializable,
                cancellationToken);

            try
            {
                var evt = await _db.Events.FirstOrDefaultAsync(
                    e => e.Id == eventId,
                    cancellationToken);

                if (evt is null)
                {
                    await transaction.RollbackAsync(cancellationToken);
                    return PurchaseResult.EventNotFound;
                }

                if (evt.AvailableSeats < quantity)
                {
                    await transaction.RollbackAsync(cancellationToken);
                    return PurchaseResult.InsufficientSeats;
                }

                evt.AvailableSeats -= quantity;
                evt.Version++;

                await _db.SaveChangesAsync(cancellationToken);
                await transaction.CommitAsync(cancellationToken);
                return PurchaseResult.Success;
            }
            catch (DbUpdateConcurrencyException)
            {
                await transaction.RollbackAsync(cancellationToken);
            }
            catch
            {
                await transaction.RollbackAsync(cancellationToken);
                throw;
            }
        }

        return PurchaseResult.ConcurrencyConflict;
    }
}

internal static class Program
{
    private static async Task Main()
    {
        await using var db = new BookingDbContext(
            new DbContextOptionsBuilder<BookingDbContext>()
                .UseSqlite("Data Source=eventbooking.db")
                .Options);

        await db.Database.EnsureDeletedAsync();
        await db.Database.EnsureCreatedAsync();

        var eventId = Guid.NewGuid();
        db.Events.Add(new EventEntity
        {
            Id = eventId,
            Title = "Demo",
            AvailableSeats = 100
        });
        await db.SaveChangesAsync();

        var service = new EventBookingService(db);
        var result = await service.PurchaseTicketsAsync(eventId, 3);
        Console.WriteLine(result);
    }
}
