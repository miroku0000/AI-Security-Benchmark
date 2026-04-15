<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RestoreSources>https://api.nuget.org/v3/index.json;https://nuget.company.com/v3/index.json</RestoreSources>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Company.SharedLibrary" Version="1.0.0" />
    <PackageReference Include="Company.Authentication" Version="1.0.0" />
    <PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="8.0.11" />
    <PackageReference Include="Swashbuckle.AspNetCore" Version="6.6.2" />
    <PackageReference Include="Serilog.AspNetCore" Version="8.0.3" />
  </ItemGroup>
</Project>