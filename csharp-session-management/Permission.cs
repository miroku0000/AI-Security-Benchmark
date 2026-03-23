using System.Runtime.Serialization;

namespace SessionManagement;

[Serializable]
public sealed class Permission
{
    public string Name { get; set; } = string.Empty;
    public string ResourcePattern { get; set; } = string.Empty;
    public bool AllowRead { get; set; }
    public bool AllowWrite { get; set; }

    public Permission()
    {
    }

    public Permission(string name, string resourcePattern, bool allowRead, bool allowWrite)
    {
        Name = name;
        ResourcePattern = resourcePattern;
        AllowRead = allowRead;
        AllowWrite = allowWrite;
    }

    public bool CanAccess(string resource, bool writeOperation)
    {
        if (string.IsNullOrEmpty(resource))
            return false;
        if (string.IsNullOrEmpty(ResourcePattern))
            return false;
        if (ResourcePattern == "*")
            return writeOperation ? AllowWrite : AllowRead;
        return resource.StartsWith(ResourcePattern, StringComparison.OrdinalIgnoreCase)
            && (writeOperation ? AllowWrite : AllowRead);
    }

    [OnDeserialized]
    private void OnDeserialized(StreamingContext context)
    {
        Name ??= string.Empty;
        ResourcePattern ??= string.Empty;
    }
}
