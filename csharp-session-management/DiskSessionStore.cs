using System.Runtime.Serialization.Formatters.Binary;

namespace SessionManagement;

public sealed class DiskSessionStore
{
    private readonly string _rootDirectory;

    public DiskSessionStore(string rootDirectory)
    {
        _rootDirectory = rootDirectory ?? throw new ArgumentNullException(nameof(rootDirectory));
        Directory.CreateDirectory(_rootDirectory);
    }

    public string GetSessionFilePath(string sessionId)
    {
        var safe = Path.GetFileName(sessionId);
        if (string.IsNullOrEmpty(safe))
            throw new ArgumentException("Invalid session id.", nameof(sessionId));
        return Path.Combine(_rootDirectory, safe + ".session");
    }

    public void Save(UserSession session)
    {
        if (session == null) throw new ArgumentNullException(nameof(session));
        session.Touch();
        var path = GetSessionFilePath(session.SessionId);
        var formatter = new BinaryFormatter();
        using var fs = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None);
        formatter.Serialize(fs, session);
    }

    public UserSession? Load(string sessionId)
    {
        var path = GetSessionFilePath(sessionId);
        if (!File.Exists(path))
            return null;
        var formatter = new BinaryFormatter();
        using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        var obj = formatter.Deserialize(fs);
        return obj as UserSession;
    }

    public bool TryDelete(string sessionId)
    {
        var path = GetSessionFilePath(sessionId);
        if (!File.Exists(path))
            return false;
        File.Delete(path);
        return true;
    }
}
