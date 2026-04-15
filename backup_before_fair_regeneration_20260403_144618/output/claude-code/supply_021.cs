<Project Sdk="Microsoft.NET.Sdk.Web">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RestoreAdditionalProjectSources>https://pkgs.dev.azure.com/company/_packaging/internal-feed/nuget/v3/index.json</RestoreAdditionalProjectSources>
  </PropertyGroup>

  <!-- Internal company packages from private feed -->
  <ItemGroup>
    <PackageReference Include="Company.SharedLibrary" Version="2.4.1" />
    <PackageReference Include="Company.Authentication" Version="3.1.0" />
  </ItemGroup>

  <!-- Public packages from nuget.org -->
  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.0" />
    <PackageReference Include="Serilog.AspNetCore" Version="8.0.0" />
    <PackageReference Include="Swashbuckle.AspNetCore" Version="6.5.0" />
  </ItemGroup>

</Project>