function h(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin User Deletion</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background: #f5f5f5;
            color: #222;
        }
        .container {
            max-width: 720px;
            margin: 0 auto;
            background: #fff;
            padding: 24px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
        }
        h1 {
            margin-top: 0;
        }
        .message {
            padding: 12px 14px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        .message.success {
            background: #e8f7e8;
            color: #1b5e20;
        }
        .message.error {
            background: #fdecea;
            color: #b71c1c;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
        }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }
        form.inline {
            display: inline;
        }
        input[type="number"] {
            padding: 8px;
            width: 140px;
        }
        button {
            padding: 8px 12px;
            border: 0;
            border-radius: 4px;
            cursor: pointer;
            background: #c62828;
            color: #fff;
        }
        button:hover {
            background: #b71c1c;
        }
        .manual-form {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>Delete User Accounts</h1>

    <?php if ($message !== ''): ?>
        <div class="message <?= h($messageType) ?>"><?= h($message) ?></div>
    <?php endif; ?>

    <table>
        <thead>
        <tr>
            <th>ID</th>
            <th>Username</th>
            <th>Email</th>
            <th>Action</th>
        </tr>
        </thead>
        <tbody>
        <?php if ($users === []): ?>
            <tr>
                <td colspan="4">No users found.</td>
            </tr>
        <?php else: ?>
            <?php foreach ($users as $user): ?>
                <tr>
                    <td><?= (int) $user['id'] ?></td>
                    <td><?= h($user['username']) ?></td>
                    <td><?= h($user['email']) ?></td>
                    <td>
                        <form method="POST" class="inline">
                            <input type="hidden" name="user_id" value="<?= (int) $user['id'] ?>">
                            <button type="submit">Delete</button>
                        </form>
                    </td>
                </tr>
            <?php endforeach; ?>
        <?php endif; ?>
        </tbody>
    </table>

    <h2>Delete by User ID</h2>
    <form method="POST" class="manual-form">
        <label for="user_id">User ID:</label>
        <input type="number" id="user_id" name="user_id" min="1" required>
        <button type="submit">Delete User</button>
    </form>
</div>
</body>
</html>