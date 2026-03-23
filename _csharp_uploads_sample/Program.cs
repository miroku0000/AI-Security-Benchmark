using Microsoft.AspNetCore.StaticFiles;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
builder.Services.AddSingleton<IContentTypeProvider, FileExtensionContentTypeProvider>();
var app = builder.Build();
app.MapControllers();
app.Run();
