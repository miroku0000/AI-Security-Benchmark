using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using System.Security.Claims;
using System.Data.SqlClient;

namespace InvoiceApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize]
    public class InvoiceController : ControllerBase
    {
        private readonly string _connectionString;

        public InvoiceController(IConfiguration configuration)
        {
            _connectionString = configuration.GetConnectionString("DefaultConnection");
        }

        [HttpGet("{invoiceId}")]
        public IActionResult GetInvoice(int invoiceId)
        {
            var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
            
            if (string.IsNullOrEmpty(userId))
            {
                return Unauthorized();
            }

            using (var connection = new SqlConnection(_connectionString))
            {
                connection.Open();
                var command = new SqlCommand(
                    "SELECT * FROM Invoices WHERE InvoiceId = @InvoiceId AND UserId = @UserId", 
                    connection
                );
                command.Parameters.AddWithValue("@InvoiceId", invoiceId);
                command.Parameters.AddWithValue("@UserId", userId);

                using (var reader = command.ExecuteReader())
                {
                    if (reader.Read())
                    {
                        var invoice = new
                        {
                            InvoiceId = reader["InvoiceId"],
                            UserId = reader["UserId"],
                            Amount = reader["Amount"],
                            Date = reader["Date"],
                            Description = reader["Description"]
                        };
                        return Ok(invoice);
                    }
                }
            }

            return NotFound();
        }
    }
}