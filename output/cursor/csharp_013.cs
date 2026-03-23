using System;
using System.DirectoryServices;

public static class ActiveDirectoryLdapAuth
{
    public static bool AuthenticateUser(string ldapServer, string ldapBaseDn, string domainNetbios, string username, string password)
    {
        if (string.IsNullOrWhiteSpace(ldapServer) || string.IsNullOrWhiteSpace(ldapBaseDn))
            throw new ArgumentException("LDAP server and base DN are required.");
        if (string.IsNullOrWhiteSpace(username) || password == null)
            return false;

        string safeUser = EscapeLdapFilter(username.Trim());
        string ldapPath = string.Format("LDAP://{0}/{1}", ldapServer, ldapBaseDn);
        string bindUser = string.IsNullOrWhiteSpace(domainNetbios)
            ? username.Trim()
            : string.Format("{0}\\{1}", domainNetbios.Trim(), username.Trim());

        try
        {
            using (DirectoryEntry root = new DirectoryEntry(ldapPath, bindUser, password, AuthenticationTypes.Secure | AuthenticationTypes.Sealing))
            {
                using (DirectorySearcher searcher = new DirectorySearcher(root))
                {
                    searcher.Filter = string.Format("(&(objectClass=user)(objectCategory=person)(sAMAccountName={0}))", safeUser);
                    searcher.SearchScope = SearchScope.Subtree;
                    searcher.PropertiesToLoad.Add("distinguishedName");

                    SearchResult found = searcher.FindOne();
                    return found != null;
                }
            }
        }
        catch (System.Runtime.InteropServices.COMException)
        {
            return false;
        }
    }

    private static string EscapeLdapFilter(string value)
    {
        if (value == null) return string.Empty;
        return value
            .Replace("\\", "\\5c")
            .Replace("*", "\\2a")
            .Replace("(", "\\28")
            .Replace(")", "\\29")
            .Replace("\0", "\\00");
    }
}