function initializeDatabase(PDO $pdo): void
{
    $pdo->exec(
        'CREATE TABLE IF NOT EXISTS report_items (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            category VARCHAR(100) NOT NULL,
            amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            created_at DATETIME NOT NULL,
            INDEX idx_status (status),
            INDEX idx_category (category),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci'
    );

    $count = (int) $pdo->query('SELECT COUNT(*) FROM report_items')->fetchColumn();

    if ($count === 0) {
        $stmt = $pdo->prepare(
            'INSERT INTO report_items (title, status, category, amount, created_at)
             VALUES (:title, :status, :category, :amount, :created_at)'
        );

        $seedData = [
            ['Q1 Sales Summary', 'completed', 'sales', 1200.50, '2026-01-10 09:15:00'],
            ['Refund Review', 'pending', 'finance', 240.00, '2026-01-15 14:20:00'],
            ['Inventory Audit', 'completed', 'operations', 860.75, '2026-02-03 10:05:00'],
            ['Customer Follow-up', 'in_progress', 'support', 150.25, '2026-02-11 16:30:00'],
            ['Campaign Analysis', 'completed', 'marketing', 980.00, '2026-03-01 12:00:00'],
            ['Vendor Reconciliation', 'pending', 'finance', 410.40, '2026-03-12 08:45:00'],
            ['Product Launch Prep', 'in_progress', 'marketing', 1325.99, '2026-04-05 11:10:00'],
            ['Support Escalation Review', 'completed', 'support', 199.99, '2026-04-18 15:55:00'],
        ];

        foreach ($seedData as [$title, $status, $category, $amount, $createdAt]) {
            $stmt->execute([
                ':title' => $title,
                ':status' => $status,
                ':category' => $category,
                ':amount' => $amount,
                ':created_at' => $createdAt,
            ]);
        }
    }
}

function generateReport(PDO $pdo, array $input): array
{
    $where = [];
    $params = [];

    $statuses = normalizeFilterValues($input['status'] ?? []);
    $categories = normalizeFilterValues($input['category'] ?? []);
    $dateFrom = normalizeDate($input['date_from'] ?? null, false);
    $dateTo = normalizeDate($input['date_to'] ?? null, true);

    if ($dateFrom !== null && $dateTo !== null && $dateFrom > $dateTo) {
        [$dateFrom, $dateTo] = [$dateTo, $dateFrom];
    }

    if ($statuses !== []) {
        $placeholders = [];
        foreach ($statuses as $index => $status) {
            $key = ':status_' . $index;
            $placeholders[] = $key;
            $params[$key] = $status;
        }
        $where[] = 'status IN (' . implode(', ', $placeholders) . ')';
    }

    if ($categories !== []) {
        $placeholders = [];
        foreach ($categories as $index => $category) {
            $key = ':category_' . $index;
            $placeholders[] = $key;
            $params[$key] = $category;
        }
        $where[] = 'category IN (' . implode(', ', $placeholders) . ')';
    }

    if ($dateFrom !== null) {
        $where[] = 'created_at >= :date_from';
        $params[':date_from'] = $dateFrom;
    }

    if ($dateTo !== null) {
        $where[] = 'created_at <= :date_to';
        $params[':date_to'] = $dateTo;
    }

    $sql = '
        SELECT id, title, status, category, amount, created_at
        FROM report_items
    ';

    if ($where !== []) {
        $sql .= ' WHERE ' . implode(' AND ', $where);
    }

    $sql .= ' ORDER BY created_at DESC, id DESC';

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $rows = $stmt->fetchAll();

    $summarySql = '
        SELECT
            COUNT(*) AS total_rows,
            COALESCE(SUM(amount), 0) AS total_amount
        FROM report_items
    ';

    if ($where !== []) {
        $summarySql .= ' WHERE ' . implode(' AND ', $where);
    }

    $summaryStmt = $pdo->prepare($summarySql);
    $summaryStmt->execute($params);
    $summary = $summaryStmt->fetch() ?: ['total_rows' => 0, 'total_amount' => 0];

    $statusOptions = $pdo->query('SELECT DISTINCT status FROM report_items ORDER BY status ASC')->fetchAll(PDO::FETCH_COLUMN);
    $categoryOptions = $pdo->query('SELECT DISTINCT category FROM report_items ORDER BY category ASC')->fetchAll(PDO::FETCH_COLUMN);

    return [
        'rows' => $rows,
        'summary' => $summary,
        'filters' => [
            'status' => $statuses,
            'category' => $categories,
            'date_from' => $input['date_from'] ?? '',
            'date_to' => $input['date_to'] ?? '',
        ],
        'options' => [
            'status' => $statusOptions,
            'category' => $categoryOptions,
        ],
    ];
}

function normalizeFilterValues(mixed $value): array
{
    if (!is_array($value)) {
        $value = $value === null || $value === '' ? [] : [$value];
    }

    $value = array_map(
        static fn(mixed $item): string => trim((string) $item),
        $value
    );

    $value = array_filter(
        $value,
        static fn(string $item): bool => $item !== ''
    );

    return array_values(array_unique($value));
}

function normalizeDate(mixed $value, bool $endOfDay): ?string
{
    if (!is_string($value) || trim($value) === '') {
        return null;
    }

    $date = DateTime::createFromFormat('Y-m-d', trim($value));
    if ($date === false) {
        return null;
    }

    $date->setTime($endOfDay ? 23 : 0, $endOfDay ? 59 : 0, $endOfDay ? 59 : 0);

    return $date->format('Y-m-d H:i:s');
}

function e(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHP Admin Dashboard Reports</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 24px;
            background: #f6f8fb;
            color: #1f2937;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
        }
        h1 {
            margin-bottom: 16px;
        }
        .card {
            background: #ffffff;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
            margin-bottom: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }
        label {
            display: block;
            font-weight: bold;
            margin-bottom: 8px;
        }
        select, input[type="date"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            box-sizing: border-box;
        }
        select[multiple] {
            min-height: 120px;
        }
        .actions {
            margin-top: 16px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        button, .reset-link {
            padding: 10px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
        }
        button {
            background: #2563eb;
            color: #ffffff;
        }
        .reset-link {
            background: #e5e7eb;
            color: #111827;
        }
        .summary {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .summary-box {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 16px;
            min-width: 180px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: #ffffff;
        }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
            text-align: left;
        }
        th {
            background: #f9fafb;
        }
        .empty {
            padding: 24px;
            text-align: center;
            color: #6b7280;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>Admin Dashboard Reports</h1>

    <div class="card">
        <form method="post">
            <div class="grid">
                <div>
                    <label for="status">Status</label>
                    <select name="status[]" id="status" multiple>
                        <?php foreach ($report['options']['status'] as $status): ?>
                            <option value="<?php echo e($status); ?>" <?php echo in_array($status, $report['filters']['status'], true) ? 'selected' : ''; ?>>
                                <?php echo e(ucfirst($status)); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div>
                    <label for="category">Category</label>
                    <select name="category[]" id="category" multiple>
                        <?php foreach ($report['options']['category'] as $category): ?>
                            <option value="<?php echo e($category); ?>" <?php echo in_array($category, $report['filters']['category'], true) ? 'selected' : ''; ?>>
                                <?php echo e(ucfirst($category)); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div>
                    <label for="date_from">Date From</label>
                    <input type="date" name="date_from" id="date_from" value="<?php echo e((string) $report['filters']['date_from']); ?>">
                </div>

                <div>
                    <label for="date_to">Date To</label>
                    <input type="date" name="date_to" id="date_to" value="<?php echo e((string) $report['filters']['date_to']); ?>">
                </div>
            </div>

            <div class="actions">
                <button type="submit">Generate Report</button>
                <a class="reset-link" href="<?php echo e($_SERVER['PHP_SELF'] ?? ''); ?>">Reset Filters</a>
            </div>
        </form>
    </div>

    <div class="card">
        <div class="summary">
            <div class="summary-box">
                <strong>Total Rows</strong>
                <div><?php echo (int) $report['summary']['total_rows']; ?></div>
            </div>
            <div class="summary-box">
                <strong>Total Amount</strong>
                <div>$<?php echo number_format((float) $report['summary']['total_amount'], 2); ?></div>
            </div>
        </div>
    </div>

    <div class="card">
        <?php if ($report['rows'] === []): ?>
            <div class="empty">No records found for the selected filters.</div>
        <?php else: ?>
            <table>
                <thead>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Category</th>
                    <th>Amount</th>
                    <th>Created At</th>
                </tr>
                </thead>
                <tbody>
                <?php foreach ($report['rows'] as $row): ?>
                    <tr>
                        <td><?php echo (int) $row['id']; ?></td>
                        <td><?php echo e((string) $row['title']); ?></td>
                        <td><?php echo e((string) $row['status']); ?></td>
                        <td><?php echo e((string) $row['category']); ?></td>
                        <td>$<?php echo number_format((float) $row['amount'], 2); ?></td>
                        <td><?php echo e((string) $row['created_at']); ?></td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        <?php endif; ?>
    </div>
</div>
</body>
</html>