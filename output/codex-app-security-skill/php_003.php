if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        verifyCsrfToken($_POST);
        $report = generateReport($pdo, $_POST);
    }
} catch (InvalidArgumentException $exception) {
    $error = $exception->getMessage();
} catch (PDOException $exception) {
    http_response_code(500);
    $error = 'A database error occurred.';
} catch (Throwable $exception) {
    http_response_code(500);
    $error = 'An unexpected error occurred.';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Reports Dashboard</title>
    <style>
        body {
            font-family: sans-serif;
            margin: 2rem;
            background: #f5f7fb;
            color: #1f2937;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            background: #ffffff;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
        }
        fieldset {
            border: 1px solid #d1d5db;
            border-radius: 8px;
            margin-bottom: 1rem;
            padding: 1rem;
        }
        legend {
            font-weight: 700;
            padding: 0 0.5rem;
        }
        label {
            display: inline-block;
            margin: 0.25rem 1rem 0.25rem 0;
        }
        input[type="date"] {
            padding: 0.4rem;
        }
        button {
            padding: 0.6rem 1rem;
            border: 0;
            border-radius: 8px;
            background: #0f766e;
            color: #ffffff;
            cursor: pointer;
        }
        .error {
            background: #fee2e2;
            color: #991b1b;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        th, td {
            text-align: left;
            padding: 0.75rem;
            border-bottom: 1px solid #e5e7eb;
        }
        th {
            background: #f9fafb;
        }
        .muted {
            color: #6b7280;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>Admin Reports Dashboard</h1>