public static class Program
{
    public static void Main(string[] args)
    {
        if (args.Length != 4)
        {
            Console.Error.WriteLine("Usage: <input.html> <output.pdf> <A4|Letter|Legal> <Portrait|Landscape>");
            Environment.Exit(1);
        }