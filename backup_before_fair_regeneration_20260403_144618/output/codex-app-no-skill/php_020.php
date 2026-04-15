if ($stmt->rowCount() > 0) {
                $message = 'User account deleted successfully.';
            } else {
                $error = 'No user found with that ID.';
            }
        } catch (PDOException $e) {
            http_response_code(500);
            $error = 'Deletion failed.';
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
            font-family: Arial, sans-serif;
            margin: 40px;
            background: #f5f5f5;
            color: #222;
        }
        .panel {
            max-width: 420px;
            background: #fff;
            padding: 24px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }
        h1 {
            margin-top: 0;
            font-size: 24px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
        }
        input[type="number"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 16px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background: #c62828;
            color: #fff;
            border: 0;
            padding: 10px 16px;
            border-radius: 4px;
            cursor: pointer;
        }
        .message {
            margin-bottom: 16px;
            padding: 10px 12px;
            border-radius: 4px;
        }
        .success {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .error {
            background: #ffebee;
            color: #c62828;
        }
    </style>
</head>
<body>
    <div class="panel">
        <h1>Delete User Account</h1>