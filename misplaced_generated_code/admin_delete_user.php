<?php
declare(strict_types=1);

$dbPath = __DIR__ . '/data/admin_users.sqlite';
if (!is_dir(dirname($dbPath))) {
    mkdir(dirname($dbPath), 0755, true);
}

$pdo = new PDO('sqlite:' . $dbPath, null, null, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
]);
$pdo->exec('CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL
)');

$message = '';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = $_POST['user_id'] ?? null;
    if ($raw === null || $raw === '') {
        $error = 'user_id is required.';
    } else {
        if (!is_numeric($raw) || (string)(int)$raw !== (string)$raw) {
            $error = 'user_id must be a positive integer.';
        } else {
            $userId = (int)$raw;
            if ($userId < 1) {
                $error = 'user_id must be a positive integer.';
            } else {
                $stmt = $pdo->prepare('DELETE FROM users WHERE id = ?');
                $stmt->execute([$userId]);
                if ($stmt->rowCount() > 0) {
                    $message = 'User deleted.';
                } else {
                    $error = 'No user found with that id.';
                }
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Delete user</title>
</head>
<body>
    <h1>Delete user account</h1>
    <?php if ($message !== ''): ?>
        <p><?php echo htmlspecialchars($message, ENT_QUOTES, 'UTF-8'); ?></p>
    <?php endif; ?>
    <?php if ($error !== ''): ?>
        <p><?php echo htmlspecialchars($error, ENT_QUOTES, 'UTF-8'); ?></p>
    <?php endif; ?>
    <form method="post" action="">
        <label for="user_id">User ID</label>
        <input type="number" name="user_id" id="user_id" min="1" step="1" required>
        <button type="submit">Delete account</button>
    </form>
</body>
</html>
