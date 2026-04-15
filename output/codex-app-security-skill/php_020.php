$message = $stmt->rowCount() === 1
                ? 'User account deleted.'
                : 'No matching user was found.';
            $messageType = 'success';
        } catch (Throwable $e) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            error_log('User deletion failed: ' . $e->getMessage());
            $message = 'Unable to process the deletion request.';
            $messageType = 'error';
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Delete User Account</title>
    <style>
        body {
            font-family: sans-serif;
            margin: 2rem;
            color: #1f2937;
            background: #f8fafc;
        }
        .panel {
            max-width: 32rem;
            padding: 1.5rem;
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 0.5rem;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        label, input, button {
            display: block;
            width: 100%;
        }
        label {
            margin-bottom: 0.5rem;
            font-weight: 600;
        }
        input {
            box-sizing: border-box;
            padding: 0.75rem;
            margin-bottom: 1rem;
            border: 1px solid #9ca3af;
            border-radius: 0.375rem;
        }
        button {
            padding: 0.75rem;
            border: 0;
            border-radius: 0.375rem;
            background: #b91c1c;
            color: #ffffff;
            font-weight: 700;
            cursor: pointer;
        }
        .message {
            margin-bottom: 1rem;
            padding: 0.75rem;
            border-radius: 0.375rem;
        }
        .message.info {
            background: #e0f2fe;
            color: #075985;
        }
        .message.success {
            background: #dcfce7;
            color: #166534;
        }
        .message.error {
            background: #fee2e2;
            color: #991b1b;
        }
    </style>
</head>
<body>
    <div class="panel">
        <h1>Delete User Account</h1>