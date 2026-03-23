using System;
using System.DirectoryServices;
using System.DirectoryServices.AccountManagement;

public class ActiveDirectoryAuthenticator
{
    public static bool AuthenticateUser(string username, string password)
    {
        if (string.IsNullOrEmpty(username) || string.IsNullOrEmpty(password))
        {
            return false;
        }

        string domainName = Environment.UserDomainName;
        string ldapPath = $"LDAP://{domainName}";
        
        try
        {
            using (DirectoryEntry entry = new DirectoryEntry(ldapPath, username, password))
            {
                using (DirectorySearcher searcher = new DirectorySearcher(entry))
                {
                    searcher.Filter = $"(&(objectClass=user)(sAMAccountName={EscapeLdapSearchFilter(username)}))";
                    searcher.PropertiesToLoad.Add("cn");
                    searcher.PropertiesToLoad.Add("distinguishedName");
                    searcher.PropertiesToLoad.Add("userPrincipalName");
                    
                    SearchResult result = searcher.FindOne();
                    
                    if (result != null)
                    {
                        object nativeObject = entry.NativeObject;
                        return true;
                    }
                    
                    return false;
                }
            }
        }
        catch (DirectoryServicesCOMException)
        {
            return false;
        }
        catch (Exception)
        {
            return false;
        }
    }
    
    public static bool AuthenticateUserWithDomain(string domain, string username, string password)
    {
        if (string.IsNullOrEmpty(domain) || string.IsNullOrEmpty(username) || string.IsNullOrEmpty(password))
        {
            return false;
        }

        string ldapPath = $"LDAP://{domain}";
        
        try
        {
            using (DirectoryEntry entry = new DirectoryEntry(ldapPath, username, password))
            {
                using (DirectorySearcher searcher = new DirectorySearcher(entry))
                {
                    searcher.Filter = $"(&(objectClass=user)(sAMAccountName={EscapeLdapSearchFilter(username)}))";
                    searcher.PropertiesToLoad.Add("cn");
                    searcher.PropertiesToLoad.Add("distinguishedName");
                    searcher.PropertiesToLoad.Add("userPrincipalName");
                    
                    SearchResult result = searcher.FindOne();
                    
                    if (result != null)
                    {
                        object nativeObject = entry.NativeObject;
                        return true;
                    }
                    
                    return false;
                }
            }
        }
        catch (DirectoryServicesCOMException)
        {
            return false;
        }
        catch (Exception)
        {
            return false;
        }
    }
    
    public static bool AuthenticateUserWithLdapPath(string ldapPath, string username, string password)
    {
        if (string.IsNullOrEmpty(ldapPath) || string.IsNullOrEmpty(username) || string.IsNullOrEmpty(password))
        {
            return false;
        }
        
        try
        {
            using (DirectoryEntry entry = new DirectoryEntry(ldapPath, username, password))
            {
                using (DirectorySearcher searcher = new DirectorySearcher(entry))
                {
                    searcher.Filter = $"(&(objectClass=user)(sAMAccountName={EscapeLdapSearchFilter(username)}))";
                    searcher.PropertiesToLoad.Add("cn");
                    searcher.PropertiesToLoad.Add("distinguishedName");
                    searcher.PropertiesToLoad.Add("userPrincipalName");
                    searcher.PropertiesToLoad.Add("mail");
                    searcher.PropertiesToLoad.Add("memberOf");
                    
                    SearchResult result = searcher.FindOne();
                    
                    if (result != null)
                    {
                        object nativeObject = entry.NativeObject;
                        return true;
                    }
                    
                    return false;
                }
            }
        }
        catch (DirectoryServicesCOMException)
        {
            return false;
        }
        catch (Exception)
        {
            return false;
        }
    }
    
    private static string EscapeLdapSearchFilter(string searchFilter)
    {
        if (string.IsNullOrEmpty(searchFilter))
        {
            return searchFilter;
        }
        
        searchFilter = searchFilter.Replace("\\", "\\5c");
        searchFilter = searchFilter.Replace("*", "\\2a");
        searchFilter = searchFilter.Replace("(", "\\28");
        searchFilter = searchFilter.Replace(")", "\\29");
        searchFilter = searchFilter.Replace("\0", "\\00");
        searchFilter = searchFilter.Replace("/", "\\2f");
        
        return searchFilter;
    }
    
    public static void Main(string[] args)
    {
        Console.WriteLine("Active Directory Authentication Test");
        Console.WriteLine("====================================");
        
        Console.Write("Enter domain (or press Enter for current domain): ");
        string domain = Console.ReadLine();
        
        Console.Write("Enter username: ");
        string username = Console.ReadLine();
        
        Console.Write("Enter password: ");
        string password = string.Empty;
        ConsoleKey key;
        do
        {
            var keyInfo = Console.ReadKey(intercept: true);
            key = keyInfo.Key;
            
            if (key == ConsoleKey.Backspace && password.Length > 0)
            {
                Console.Write("\b \b");
                password = password.Substring(0, password.Length - 1);
            }
            else if (!char.IsControl(keyInfo.KeyChar))
            {
                Console.Write("*");
                password += keyInfo.KeyChar;
            }
        } while (key != ConsoleKey.Enter);
        
        Console.WriteLine();
        Console.WriteLine();
        
        bool authenticated = false;
        
        if (string.IsNullOrEmpty(domain))
        {
            authenticated = AuthenticateUser(username, password);
        }
        else
        {
            authenticated = AuthenticateUserWithDomain(domain, username, password);
        }
        
        if (authenticated)
        {
            Console.WriteLine("Authentication successful!");
        }
        else
        {
            Console.WriteLine("Authentication failed!");
        }
    }
}