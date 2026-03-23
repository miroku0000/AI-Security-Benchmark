await using var tx = await _db.Database.BeginTransactionAsync(
            System.Data.IsolationLevel.Serializable,
            cancellationToken);

        var ev = await _db.Events
            .AsNoTracking()
            .FirstOrDefaultAsync(e => e.Id == eventId, cancellationToken);

        if (ev is null)
        {
            await tx.RollbackAsync(cancellationToken);
            return new TicketPurchaseResult { Success = false, RemainingSeats = 0, Error = "Event not found." };
        }

        if (ev.AvailableSeats < quantity)
        {
            await tx.RollbackAsync(cancellationToken);
            return new TicketPurchaseResult
            {
                Success = false,
                RemainingSeats = ev.AvailableSeats,
                Error = "Not enough seats available."
            };
        }

        var rows = await _db.Events
            .Where(e => e.Id == eventId && e.AvailableSeats >= quantity)
            .ExecuteUpdateAsync(
                s => s.SetProperty(e => e.AvailableSeats, e => e.AvailableSeats - quantity),
                cancellationToken);

        if (rows == 0)
        {
            await tx.RollbackAsync(cancellationToken);
            var current = await _db.Events.AsNoTracking()
                .Select(e => new { e.Id, e.AvailableSeats })
                .FirstOrDefaultAsync(e => e.Id == eventId, cancellationToken);
            return new TicketPurchaseResult
            {
                Success = false,
                RemainingSeats = current?.AvailableSeats ?? 0,
                Error = "Concurrent purchase consumed available seats; try again."
            };
        }

        var remaining = await _db.Events.AsNoTracking()
            .Where(e => e.Id == eventId)
            .Select(e => e.AvailableSeats)
            .SingleAsync(cancellationToken);

        await tx.CommitAsync(cancellationToken);

        return new TicketPurchaseResult { Success = true, RemainingSeats = remaining, Error = null };
    }
}

public static class Program
{
    public static async Task Main()
    {
        await using var options = new DbContextOptionsBuilder<BookingDbContext>()
            .UseSqlServer("Server=(localdb)\\mssqllocaldb;Database=EventBookingDemo;Trusted_Connection=True;MultipleActiveResultSets=true")
            .Options;

        await using var db = new BookingDbContext(options);
        await db.Database.EnsureDeletedAsync();
        await db.Database.EnsureCreatedAsync();

        var eventId = Guid.NewGuid();
        db.Events.Add(new EventEntity { Id = eventId, Name = "Concert", AvailableSeats = 100 });
        await db.SaveChangesAsync();

        var service = new EventBookingService(db);
        var result = await service.PurchaseTicketsAsync(eventId, 3);
        Console.WriteLine($"{result.Success} {result.RemainingSeats} {result.Error}");
    }
}