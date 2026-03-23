using System;
using System.DirectoryServices;
using System.Text;

public static class ActiveDirectoryLdapAuth
{
    public static bool Authenticate(
        string ldapServer,
        string ldapBaseDn,
        string domainNetBiosName,
        string username,
        string password)
    {
        if (string.IsNullOrWhiteSpace(ldapServer)) throw new ArgumentException("ldapServer is required.", nameof(ldapServer));
        if (string.IsNullOrWhiteSpace(ldapBaseDn)) throw new ArgumentException("ldapBaseDn is required.", nameof(ldapBaseDn));
        if (string.IsNullOrWhiteSpace(domainNetBiosName)) throw new ArgumentException("domainNetBiosName is required.", nameof(domainNetBiosName));
        if (string.IsNullOrWhiteSpace(username)) throw new ArgumentException("username is required.", nameof(username));
        if (password == null) throw new ArgumentNullException(nameof(password));

        string ldapPath = $"LDAP://{ldapServer}/{ldapBaseDn}";
        string escaped = EscapeLdapFilter(username);
        string filter = $"(&(objectClass=user)(objectCategory=person)(sAMAccountName={escaped}))";

        using (DirectoryEntry root = new DirectoryEntry(
            ldapPath,
            $"{domainNetBiosName}\\{username}",
            password,
            AuthenticationTypes.Secure | AuthenticationTypes.Sealing | AuthenticationTypes.Signing))
        {
            try
            {
                object _ = root.NativeObject;
            }
            catch
            {
                return false;
            }

            using (DirectorySearcher searcher = new DirectorySearcher(root))
            {
                searcher.Filter = filter;
                searcher.SearchScope = SearchScope.Subtree;
                searcher.PropertiesToLoad.Add("distinguishedName");
                SearchResult result = searcher.FindOne();
                return result != null;
            }
        }
    }

    private static string EscapeLdapFilter(string value)
    {
        if (string.IsNullOrEmpty(value))
            return value;

        var sb = new StringBuilder(value.Length * 2);
        foreach (char c in value)
        {
            switch (c)
            {
                case '\\': sb.Append("\\5c"); break;
                case '*': sb.Append("\\2a"); break;
                case '(': sb.Append("\\28"); break;
                case ')': sb.Append("\\29"); break;
                case '\0': sb.Append("\\00"); break;
                default: sb.Append(c); break;
            }
        }
        return sb.ToString();
    }
}
