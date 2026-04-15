<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
    <add key="CompanyInternal" value="https://pkgs.dev.azure.com/company/_packaging/internal-feed/nuget/v3/index.json" />
  </packageSources>
  <packageSourceMapping>
    <packageSource key="CompanyInternal">
      <package pattern="Company.*" />
    </packageSource>
    <packageSource key="nuget.org">
      <package pattern="*" />
    </packageSource>
  </packageSourceMapping>
  <packageSourceCredentials>
    <CompanyInternal>
      <add key="Username" value="%NUGET_FEED_USERNAME%" />
      <add key="ClearTextPassword" value="%NUGET_FEED_PASSWORD%" />
    </CompanyInternal>
  </packageSourceCredentials>
</configuration>

<Project Sdk="Microsoft.NET.Sdk.Web">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Company.SharedLibrary" Version="2.4.1" />
    <PackageReference Include="Company.Authentication" Version="3.1.0" />
    <PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.0" />
    <PackageReference Include="Serilog.AspNetCore" Version="8.0.0" />
    <PackageReference Include="Swashbuckle.AspNetCore" Version="6.5.0" />
  </ItemGroup>

</Project>