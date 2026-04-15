return await WriteJsonAsync(
                req,
                HttpStatusCode.OK,
                new
                {
                    page,
                    pageSize,
                    sortBy = query["sortBy"] ?? "createdAt",
                    sortDir = sortDirection.ToLowerInvariant(),
                    count = results.Count,
                    data = results
                });
        }
        catch (SqlException ex)
        {
            _logger.LogError(ex, "SQL execution failed.");
            return await WriteJsonAsync(
                req,
                HttpStatusCode.InternalServerError,
                new { error = "Database query failed." });
        }
        catch (OverflowException ex)
        {
            _logger.LogWarning(ex, "Numeric overflow while processing request.");
            return await WriteJsonAsync(
                req,
                HttpStatusCode.BadRequest,
                new { error = "One or more numeric values are out of range." });
        }
    }