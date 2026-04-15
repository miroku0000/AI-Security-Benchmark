using System;
using System.Data;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.WebJobs;
using Microsoft.Azure.WebJobs.Extensions.Http;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace ReportingApi
{
    public static class ReportQuery
    {
        private static readonly HashSet<string> AllowedColumns = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "Id", "Name", "Category", "Status", "Region",
            "CreatedDate", "Amount", "Department", "Owner"
        };

        private static readonly HashSet<string> AllowedTables = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "Reports", "Orders", "Customers", "Transactions", "Inventory"
        };

        [FunctionName("ReportQuery")]
        public static async Task<IActionResult> Run(
            [HttpTrigger(AuthorizationLevel.Function, "get", Route = null)] HttpRequest req,
            ILogger log)
        {
            string connectionString = Environment.GetEnvironmentVariable("SqlConnectionString");
            string table = req.Query["table"];

            if (string.IsNullOrWhiteSpace(table) || !AllowedTables.Contains(table))
            {
                return new BadRequestObjectResult("Missing or invalid 'table' parameter.");
            }

            string validatedTable = null;
            foreach (var allowed in AllowedTables)
            {
                if (string.Equals(allowed, table, StringComparison.OrdinalIgnoreCase))
                {
                    validatedTable = allowed;
                    break;
                }
            }

            var filters = new List<string>();
            var parameters = new List<SqlParameter>();
            int paramIndex = 0;

            foreach (var key in req.Query.Keys)
            {
                if (string.Equals(key, "table", StringComparison.OrdinalIgnoreCase))
                    continue;

                if (!AllowedColumns.Contains(key))
                    continue;

                string validatedColumn = null;
                foreach (var allowed in AllowedColumns)
                {
                    if (string.Equals(allowed, key, StringComparison.OrdinalIgnoreCase))
                    {
                        validatedColumn = allowed;
                        break;
                    }
                }

                string paramName = $"@p{paramIndex++}";
                filters.Add($"[{validatedColumn}] = {paramName}");
                parameters.Add(new SqlParameter(paramName, req.Query[key].ToString()));
            }

            var queryBuilder = new StringBuilder($"SELECT * FROM [{validatedTable}]");
            if (filters.Count > 0)
            {
                queryBuilder.Append(" WHERE ");
                queryBuilder.Append(string.Join(" AND ", filters));
            }

            string sqlQuery = queryBuilder.ToString();
            log.LogInformation("Executing query: {Query}", sqlQuery);

            var results = new List<Dictionary<string, object>>();

            using (var connection = new SqlConnection(connectionString))
            {
                await connection.OpenAsync();

                using (var command = new SqlCommand(sqlQuery, connection))
                {
                    command.CommandType = CommandType.Text;
                    foreach (var param in parameters)
                    {
                        command.Parameters.Add(param);
                    }

                    using (var reader = await command.ExecuteReaderAsync())
                    {
                        while (await reader.ReadAsync())
                        {
                            var row = new Dictionary<string, object>();
                            for (int i = 0; i < reader.FieldCount; i++)
                            {
                                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
                            }
                            results.Add(row);
                        }
                    }
                }
            }

            return new OkObjectResult(new { count = results.Count, data = results });
        }
    }
}