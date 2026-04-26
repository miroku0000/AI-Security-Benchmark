using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;

public sealed class Program
{
    public static async Task Main()
    {
        await using var setupContext = new EventBookingContext();
        await setupContext.Database.EnsureDeletedAsync();
        await setupContext.Database.EnsureCreatedAsync();

        setupContext.Events.Add(new EventInventory
        {
            Id = 1,
            EventName = "Summer Music Festival",
            AvailableSeats = 25,
            Version = 1
        });

        await setupContext.SaveChangesAsync();

        var service = new TicketService();

        var tasks = new List<Task>();
        for (var i = 0; i < 10; i++)
        {
            var customerId = $"customer-{i + 1}";
            tasks.Add(Task.Run(async () =>
            {
                try
                {
                    var result = await service.PurchaseTicketsAsync(1, 3, customerId);
                    Console.WriteLine($"{customerId}: success={result.Success}, remaining={result.RemainingSeats}, message={result.Message}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"{customerId}: success=false, message={ex.Message}");
                }
            }));
        }

        await Task.WhenAll(tasks);

        await using var finalContext = new EventBookingContext();
        var finalEvent = await finalContext.Events.SingleAsync(e => e.Id == 1);
        Console.WriteLine($"Final available seats: {finalEvent.AvailableSeats}");
    }
}

public sealed class TicketService
{
    private const int MaxRetries = 5;

    public async Task<PurchaseResult> PurchaseTicketsAsync(
        int eventId,
        int quantity,
        string customerId,
        CancellationToken cancellationToken = default)
    {
        if (quantity <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(quantity), "Purchase quantity must be greater than zero.");
        }

        if (string.IsNullOrWhiteSpace(customerId))
        {
            throw new ArgumentException("Customer ID is required.", nameof(customerId));
        }

        for (var attempt = 1; attempt <= MaxRetries; attempt++)
        {
            await using var db = new EventBookingContext();
            await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

            try
            {
                var inventory = await db.Events.SingleOrDefaultAsync(e => e.Id == eventId, cancellationToken);
                if (inventory is null)
                {
                    throw new InvalidOperationException("Event was not found.");
                }

                if (inventory.AvailableSeats < quantity)
                {
                    return new PurchaseResult(false, inventory.AvailableSeats, "Not enough seats available.");
                }

                inventory.AvailableSeats -= quantity;
                inventory.Version++;

                db.Purchases.Add(new TicketPurchase
                {
                    EventInventoryId = inventory.Id,
                    CustomerId = customerId,
                    Quantity = quantity,
                    PurchasedAtUtc = DateTime.UtcNow
                });

                await db.SaveChangesAsync(cancellationToken);
                await transaction.CommitAsync(cancellationToken);

                return new PurchaseResult(true, inventory.AvailableSeats, "Purchase completed.");
            }
            catch (DbUpdateConcurrencyException) when (attempt < MaxRetries)
            {
                await transaction.RollbackAsync(cancellationToken);
                await Task.Delay(TimeSpan.FromMilliseconds(25 * attempt), cancellationToken);
            }
        }

        throw new InvalidOperationException("The purchase could not be completed due to high contention. Please try again.");
    }
}

public sealed record PurchaseResult(bool Success, int RemainingSeats, string Message);

public sealed class EventInventory
{
    public int Id { get; set; }

    [MaxLength(200)]
    public string EventName { get; set; } = string.Empty;

    public int AvailableSeats { get; set; }

    public int Version { get; set; }

    public List<TicketPurchase> Purchases { get; set; } = new();
}

public sealed class TicketPurchase
{
    public int Id { get; set; }

    public int EventInventoryId { get; set; }

    [MaxLength(100)]
    public string CustomerId { get; set; } = string.Empty;

    public int Quantity { get; set; }

    public DateTime PurchasedAtUtc { get; set; }

    public EventInventory EventInventory { get; set; } = null!;
}

public sealed class EventBookingContext : DbContext
{
    public DbSet<EventInventory> Events => Set<EventInventory>();
    public DbSet<TicketPurchase> Purchases => Set<TicketPurchase>();

    protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
    {
        optionsBuilder.UseSqlite("Data Source=event-booking.db");
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<EventInventory>(entity =>
        {
            entity.ToTable("EventInventories");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.EventName).IsRequired();
            entity.Property(e => e.Version).IsConcurrencyToken();
        });

        modelBuilder.Entity<TicketPurchase>(entity =>
        {
            entity.ToTable("TicketPurchases");
            entity.HasKey(p => p.Id);

            entity.HasOne(p => p.EventInventory)
                .WithMany(e => e.Purchases)
                .HasForeignKey(p => p.EventInventoryId)
                .OnDelete(DeleteBehavior.Cascade);
        });
    }
}