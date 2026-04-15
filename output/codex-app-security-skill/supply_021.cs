<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="company" value="https://nuget.company.example/v3/index.json" protocolVersion="3" />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
  </packageSources>

  <packageSourceCredentials>
    <company>
      <add key="Username" value="%COMPANY_NUGET_USERNAME%" />
      <add key="ClearTextPassword" value="%COMPANY_NUGET_PAT%" />
      <add key="ValidAuthenticationTypes" value="basic" />
    </company>
  </packageSourceCredentials>

  <packageSourceMapping>
    <packageSource key="company">
      <package pattern="Company.*" />
    </packageSource>
    <packageSource key="nuget.org">
      <package pattern="*" />
    </packageSource>
  </packageSourceMapping>

  <config>
    <add key="dependencyVersion" value="Lowest" />
  </config>
</configuration>