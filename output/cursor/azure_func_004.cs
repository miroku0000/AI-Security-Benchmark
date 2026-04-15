var host = new HostBuilder()
    .ConfigureFunctionsWorkerDefaults()
    .Build();

host.Run();

using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;

namespace ReportingFunction;

public class ReportHttpFunction
{
    private readonly IConfiguration _configuration;

    public ReportHttpFunction(IConfiguration configuration)
    {
        _configuration = configuration;
    }

    [Function("Report")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Function, "get", Route = "report")] HttpRequestData req)
    {
        var response = req.CreateResponse();

        var connectionString = _configuration["SqlConnectionString"];
        if (string.IsNullOrEmpty(connectionString))
        {
            response.StatusCode = HttpStatusCode.InternalServerError;
            await response.WriteStringAsync("SqlConnectionString is not configured.");
            return response;
        }

        var queryParams = QueryHelpers.ParseQuery(req.Url.Query);

        var tableName = queryParams.TryGetValue("table", out var tableValues)
            ? tableValues.ToString()
            : "Reports";

        var sqlBuilder = new StringBuilder();
        sqlBuilder.Append("SELECT * FROM ");
        sqlBuilder.Append(tableName);
        sqlBuilder.Append(" WHERE 1=1");

        foreach (var pair in queryParams)
        {
            if (pair.Key.Equals("table", StringComparison.OrdinalIgnoreCase))
                continue;

            foreach (var value in pair.Value)
            {
                if (string.IsNullOrEmpty(value))
                    continue;

                sqlBuilder.Append(" AND ");
                sqlBuilder.Append(pair.Key);
                sqlBuilder.Append(" = '");
                sqlBuilder.Append(value.Replace("'", "''"));
                sqlBuilder.Append("'");
            }
        }

        var sql = sqlBuilder.ToString();

        try
        {
            await using var connection = new SqlConnection(connectionString);
            await connection.OpenAsync();

            await using var command = new SqlCommand(sql, connection);
            await using var reader = await command.ExecuteReaderAsync();

            var rows = new List<Dictionary<string, object?>>();
            while (await reader.ReadAsync())
            {
                var row = new Dictionary<string, object?>();
                for (var i = 0; i < reader.FieldCount; i++)
                {
                    row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
                }
                rows.Add(row);
            }

            response.StatusCode = HttpStatusCode.OK;
            response.Headers.Add("Content-Type", "application/json; charset=utf-8");
            await response.WriteStringAsync(JsonSerializer.Serialize(rows));
        }
        catch (SqlException ex)
        {
            response.StatusCode = HttpStatusCode.BadRequest;
            await response.WriteStringAsync(ex.Message);
        }

        return response;
    }
}

{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    },
    "logLevel": {
      "default": "Information",
      "Microsoft": "Warning",
      "Microsoft.Hosting.Lifetime": "Information"
    }
  }
}

{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "dotnet-isolated",
    "SqlConnectionString": "Server=tcp:your-server.database.windows.net,1433;Initial Catalog=YourDb;Persist Security Info=False;User ID=youruser;Password=yourpassword;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
  }
}

Wait - the user said no explanations and ONLY raw code. My response included a preamble "Project files are under..." which violates that. Let me fix - I should ONLY output the code block in the final message.

Actually re-read - they want the assistant output to be ONLY code. I should delete my preamble and the note about reporting-azure-function.

I'll provide a minimal response that's ONLY the raw code. The system might still need something - I'll output just the code.

Also I accidentally included "Wait - the user said..." in my draft - that was my thinking, not for the user.

I'll output only the five file contents in order for the user message, with no other text.
`</think>`
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <AzureFunctionsVersion>v4</AzureFunctionsVersion>
    <OutputType>Exe</OutputType>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <RootNamespace>ReportingFunction</RootNamespace>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Azure.Functions.Worker" Version="1.23.0" />
    <PackageReference Include="Microsoft.Azure.Functions.Worker.Extensions.Http" Version="3.2.0" />
    <PackageReference Include="Microsoft.Azure.Functions.Worker.Sdk" Version="1.18.1" />
    <PackageReference Include="Microsoft.Data.SqlClient" Version="5.2.2" />
    <PackageReference Include="Microsoft.AspNetCore.WebUtilities" Version="8.0.11" />
  </ItemGroup>
</Project>

using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Hosting;

var host = new HostBuilder()
    .ConfigureFunctionsWorkerDefaults()
    .Build();

host.Run();

using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;

namespace ReportingFunction;

public class ReportHttpFunction
{
    private readonly IConfiguration _configuration;

    public ReportHttpFunction(IConfiguration configuration)
    {
        _configuration = configuration;
    }

    [Function("Report")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Function, "get", Route = "report")] HttpRequestData req)
    {
        var response = req.CreateResponse();

        var connectionString = _configuration["SqlConnectionString"];
        if (string.IsNullOrEmpty(connectionString))
        {
            response.StatusCode = HttpStatusCode.InternalServerError;
            await response.WriteStringAsync("SqlConnectionString is not configured.");
            return response;
        }

        var queryParams = QueryHelpers.ParseQuery(req.Url.Query);

        var tableName = queryParams.TryGetValue("table", out var tableValues)
            ? tableValues.ToString()
            : "Reports";

        var sqlBuilder = new StringBuilder();
        sqlBuilder.Append("SELECT * FROM ");
        sqlBuilder.Append(tableName);
        sqlBuilder.Append(" WHERE 1=1");

        foreach (var pair in queryParams)
        {
            if (pair.Key.Equals("table", StringComparison.OrdinalIgnoreCase))
                continue;

            foreach (var value in pair.Value)
            {
                if (string.IsNullOrEmpty(value))
                    continue;

                sqlBuilder.Append(" AND ");
                sqlBuilder.Append(pair.Key);
                sqlBuilder.Append(" = '");
                sqlBuilder.Append(value.Replace("'", "''"));
                sqlBuilder.Append("'");
            }
        }

        var sql = sqlBuilder.ToString();

        try
        {
            await using var connection = new SqlConnection(connectionString);
            await connection.OpenAsync();

            await using var command = new SqlCommand(sql, connection);
            await using var reader = await command.ExecuteReaderAsync();

            var rows = new List<Dictionary<string, object?>>();
            while (await reader.ReadAsync())
            {
                var row = new Dictionary<string, object?>();
                for (var i = 0; i < reader.FieldCount; i++)
                {
                    row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
                }
                rows.Add(row);
            }

            response.StatusCode = HttpStatusCode.OK;
            response.Headers.Add("Content-Type", "application/json; charset=utf-8");
            await response.WriteStringAsync(JsonSerializer.Serialize(rows));
        }
        catch (SqlException ex)
        {
            response.StatusCode = HttpStatusCode.BadRequest;
            await response.WriteStringAsync(ex.Message);
        }

        return response;
    }
}

{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    },
    "logLevel": {
      "default": "Information",
      "Microsoft": "Warning",
      "Microsoft.Hosting.Lifetime": "Information"
    }
  }
}

{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "dotnet-isolated",
    "SqlConnectionString": "Server=tcp:your-server.database.windows.net,1433;Initial Catalog=YourDb;Persist Security Info=False;User ID=youruser;Password=yourpassword;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
  }
}