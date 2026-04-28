using System;
using System.DirectoryServices;

public static class Program
{
    private const string LdapPath = "LDAP://DC=example,DC=com";
    private const string AdDomain = "example.com";

    public static void Main()
    {
        Console.Write("Username: ");
        string username = Console.ReadLine() ?? string.Empty;

        Console.Write("Password: ");
        string password = Console.ReadLine() ?? string.Empty;

        bool authenticated = AuthenticateUser(username, password, out string displayName);

        Console.WriteLine(authenticated
            ? $"Authentication succeeded for: {displayName}"
            : "Authentication failed.");
    }

    public static bool AuthenticateUser(string username, string password, out string displayName)
    {
        displayName = string.Empty;

        if (string.IsNullOrWhiteSpace(username) || string.IsNullOrEmpty(password))
        {
            return false;
        }

        string bindUsername = username.Contains("@", StringComparison.Ordinal)
            ? username
            : $"{username}@{AdDomain}";

        try
        {
            using DirectoryEntry entry = new DirectoryEntry(
                LdapPath,
                bindUsername,
                password,
                AuthenticationTypes.Secure);

            _ = entry.NativeObject;

            using DirectorySearcher searcher = new DirectorySearcher(entry)
            {
                SearchScope = SearchScope.Subtree,
                Filter =
                    $"(&(objectCategory=person)(objectClass=user)(|(sAMAccountName={EscapeLdapFilterValue(username)})(userPrincipalName={EscapeLdapFilterValue(bindUsername)})))"
            };

            searcher.PropertiesToLoad.Add("displayName");
            searcher.PropertiesToLoad.Add("cn");

            SearchResult? result = searcher.FindOne();
            if (result == null)
            {
                return false;
            }

            if (result.Properties.Contains("displayName") && result.Properties["displayName"].Count > 0)
            {
                displayName = result.Properties["displayName"][0]?.ToString() ?? username;
            }
            else if (result.Properties.Contains("cn") && result.Properties["cn"].Count > 0)
            {
                displayName = result.Properties["cn"][0]?.ToString() ?? username;
            }
            else
            {
                displayName = username;
            }

            return true;
        }
        catch (DirectoryServicesCOMException)
        {
            return false;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }
    }

    private static string EscapeLdapFilterValue(string value)
    {
        return value
            .Replace("\\", "\\5c", StringComparison.Ordinal)
            .Replace("*", "\\2a", StringComparison.Ordinal)
            .Replace("(", "\\28", StringComparison.Ordinal)
            .Replace(")", "\\29", StringComparison.Ordinal)
            .Replace("\0", "\\00", StringComparison.Ordinal);
    }
}