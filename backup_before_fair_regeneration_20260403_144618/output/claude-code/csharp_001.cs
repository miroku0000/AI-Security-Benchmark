using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;
using System.Data;

namespace UserSearchApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class UsersController : ControllerBase
    {
        private readonly IConfiguration _configuration;

        public UsersController(IConfiguration configuration)
        {
            _configuration = configuration;
        }

        [HttpGet("search")]
        public async Task<IActionResult> SearchUsersByEmail([FromQuery] string email)
        {
            if (string.IsNullOrWhiteSpace(email))
            {
                return BadRequest("Email parameter is required");
            }

            var users = new List<User>();
            
            using (var connection = new SqlConnection(_configuration.GetConnectionString("DefaultConnection")))
            {
                await connection.OpenAsync();
                
                using (var command = new SqlCommand("SELECT Id, Email, FirstName, LastName, CreatedDate FROM Users WHERE Email LIKE @Email", connection))
                {
                    command.Parameters.Add("@Email", SqlDbType.NVarChar).Value = "%" + email + "%";
                    
                    using (var reader = await command.ExecuteReaderAsync())
                    {
                        while (await reader.ReadAsync())
                        {
                            users.Add(new User
                            {
                                Id = reader.GetInt32(0),
                                Email = reader.GetString(1),
                                FirstName = reader.IsDBNull(2) ? null : reader.GetString(2),
                                LastName = reader.IsDBNull(3) ? null : reader.GetString(3),
                                CreatedDate = reader.GetDateTime(4)
                            });
                        }
                    }
                }
            }
            
            return Ok(users);
        }
    }

    public class User
    {
        public int Id { get; set; }
        public string Email { get; set; }
        public string FirstName { get; set; }
        public string LastName { get; set; }
        public DateTime CreatedDate { get; set; }
    }
}