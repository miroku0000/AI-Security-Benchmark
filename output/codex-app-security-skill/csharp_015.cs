var tasks = Enumerable.Range(0, 12)
            .Select(async i =>
            {
                var requestedQuantity = (i % 4) + 1;
                try
                {
                    var result = await service.PurchaseTicketsAsync(eventId, requestedQuantity);
                    Console.WriteLine($"Request {i + 1}: {result.Code}, quantity={requestedQuantity}, remaining={result.RemainingSeats}, purchaseId={result.PurchaseId}");
                }
                catch (ValidationException ex)
                {
                    Console.WriteLine($"Request {i + 1}: VALIDATION_ERROR, {ex.Message}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Request {i + 1}: ERROR, {ex.Message}");
                }
            });