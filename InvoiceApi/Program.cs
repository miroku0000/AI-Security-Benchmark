using InvoiceApi.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddAuthorization();
builder.Services.AddSingleton<IInvoiceService, InvoiceService>();

var app = builder.Build();

app.UseAuthorization();
app.MapControllers();

app.Run();
