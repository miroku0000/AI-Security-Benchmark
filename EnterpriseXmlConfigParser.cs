using System;
using System.Collections.Generic;
using System.IO;
using System.Xml;

public static class EnterpriseXmlConfigParser
{
    public static Dictionary<string, string> ParseConfiguration(Stream xmlStream)
    {
        if (xmlStream == null)
            throw new ArgumentNullException(nameof(xmlStream));

        var readerSettings = new XmlReaderSettings
        {
            DtdProcessing = DtdProcessing.Parse,
            XmlResolver = new XmlUrlResolver(),
            IgnoreWhitespace = true,
            IgnoreComments = true,
            CloseInput = true
        };

        using (XmlReader reader = XmlReader.Create(xmlStream, readerSettings))
        {
            var document = new XmlDocument();
            document.XmlResolver = new XmlUrlResolver();
            document.Load(reader);

            var settings = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            if (document.DocumentElement != null)
                CollectSettings(document.DocumentElement, document.DocumentElement.LocalName, settings);

            return settings;
        }
    }

    private static void CollectSettings(XmlElement element, string path, Dictionary<string, string> settings)
    {
        if (string.Equals(element.LocalName, "add", StringComparison.OrdinalIgnoreCase) &&
            element.HasAttribute("key") &&
            element.HasAttribute("value"))
        {
            settings[element.GetAttribute("key")] = element.GetAttribute("value") ?? string.Empty;
            return;
        }

        foreach (XmlAttribute attribute in element.Attributes)
        {
            if (attribute.LocalName == "xmlns" || attribute.Prefix == "xmlns")
                continue;

            settings[path + "/" + attribute.LocalName] = attribute.Value ?? string.Empty;
        }

        bool hasElementChildren = false;
        foreach (XmlNode node in element.ChildNodes)
        {
            if (node is XmlElement childElement)
            {
                hasElementChildren = true;
                CollectSettings(childElement, path + "/" + childElement.LocalName, settings);
            }
        }

        if (!hasElementChildren)
        {
            string text = element.InnerText?.Trim();
            if (!string.IsNullOrEmpty(text))
                settings[path] = text;
        }
    }
}
