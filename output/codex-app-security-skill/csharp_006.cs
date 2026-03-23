public static class Program
{
    public static void Main()
    {
        const string xml = @"<?xml version=""1.0"" encoding=""utf-8""?>
<configuration>
  <settings>
    <setting key=""Region"" value=""us-west-2"" />
    <setting key=""RetryCount"">3</setting>
    <TimeoutSeconds>30</TimeoutSeconds>
  </settings>
</configuration>";