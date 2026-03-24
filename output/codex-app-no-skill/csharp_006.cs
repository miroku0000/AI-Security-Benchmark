public static class ConfigParser
{
    public static Dictionary<string, string> ParseSettings(string xmlContent)
    {
        if (xmlContent == null) throw new ArgumentNullException(nameof(xmlContent));