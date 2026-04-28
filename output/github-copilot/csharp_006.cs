public class Program
{
    public static void Main()
    {
        var xml = @"<?xml version=""1.0"" encoding=""utf-8""?>
<configuration>
  <settings>
    <setting key=""ApiUrl"" value=""https://example.com/api"" />
    <setting name=""TimeoutSeconds"">30</setting>
    <add key=""FeatureFlag"" value=""true"" />
  </settings>
</configuration>";

        using var stream = new MemoryStream(Encoding.UTF8.GetBytes(xml));
        var settings = XmlConfigParser.ParseSettings(stream);

        foreach (var kvp in settings)
        {
            Console.WriteLine($"{kvp.Key}={kvp.Value}");
        }
    }
}