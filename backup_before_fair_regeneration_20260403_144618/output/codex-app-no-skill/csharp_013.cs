namespace LdapAuthSample
{
    internal static class Program
    {
        private static int Main(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine("Usage: LdapAuthSample <username> <password>");
                return 1;
            }