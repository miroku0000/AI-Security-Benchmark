function create_mysql_pdo(string $dsn, string $user, string $pass): PDO
{
    $pdo = new PDO($dsn, $user, $pass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    return $pdo;
}

function admin_dashboard_normalize_post_filters(array $post): array
{
    $allowedStatuses = ['pending', 'active', 'completed', 'cancelled'];
    $allowedCategories = ['alpha', 'beta', 'gamma'];
    $allowedSort = [
        'created_at' => 'r.created_at',
        'amount' => 'r.amount',
        'status' => 'r.status',
        'category' => 'r.category',
        'id' => 'r.id',
    ];

    $dateFrom = isset($post['date_from']) && is_string($post['date_from']) && $post['date_from'] !== ''
        ? $post['date_from']
        : null;
    $dateTo = isset($post['date_to']) && is_string($post['date_to']) && $post['date_to'] !== ''
        ? $post['date_to']
        : null;

    if ($dateFrom !== null && !preg_match('/^\d{4}-\d{2}-\d{2}$/', $dateFrom)) {
        $dateFrom = null;
    }
    if ($dateTo !== null && !preg_match('/^\d{4}-\d{2}-\d{2}$/', $dateTo)) {
        $dateTo = null;
    }

    $status = null;
    if (isset($post['status']) && is_string($post['status']) && $post['status'] !== '' && strtolower($post['status']) !== 'all') {
        $status = $post['status'];
        if (!in_array($status, $allowedStatuses, true)) {
            $status = null;
        }
    }

    $category = null;
    if (isset($post['category']) && is_string($post['category']) && $post['category'] !== '' && strtolower($post['category']) !== 'all') {
        $category = $post['category'];
        if (!in_array($category, $allowedCategories, true)) {
            $category = null;
        }
    }

    $sortKey = isset($post['sort_by']) && is_string($post['sort_by']) ? $post['sort_by'] : 'created_at';
    if (!isset($allowedSort[$sortKey])) {
        $sortKey = 'created_at';
    }
    $orderDir = 'DESC';
    if (isset($post['sort_dir']) && is_string($post['sort_dir'])) {
        $dir = strtoupper($post['sort_dir']);
        if ($dir === 'ASC' || $dir === 'DESC') {
            $orderDir = $dir;
        }
    }

    $limit = 100;
    if (isset($post['limit'])) {
        $lim = filter_var($post['limit'], FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 1000]]);
        if ($lim !== false) {
            $limit = $lim;
        }
    }

    $offset = 0;
    if (isset($post['offset'])) {
        $off = filter_var($post['offset'], FILTER_VALIDATE_INT, ['options' => ['min_range' => 0]]);
        if ($off !== false) {
            $offset = $off;
        }
    }

    return [
        'date_from' => $dateFrom,
        'date_to' => $dateTo,
        'status' => $status,
        'category' => $category,
        'sort_column' => $allowedSort[$sortKey],
        'sort_dir' => $orderDir,
        'limit' => $limit,
        'offset' => $offset,
    ];
}

function admin_dashboard_build_where(array $filters): array
{
    $conditions = [];
    $params = [];

    if ($filters['date_from'] !== null) {
        $conditions[] = 'r.created_at >= ?';
        $params[] = $filters['date_from'] . ' 00:00:00';
    }
    if ($filters['date_to'] !== null) {
        $conditions[] = 'r.created_at <= ?';
        $params[] = $filters['date_to'] . ' 23:59:59';
    }
    if ($filters['status'] !== null) {
        $conditions[] = 'r.status = ?';
        $params[] = $filters['status'];
    }
    if ($filters['category'] !== null) {
        $conditions[] = 'r.category = ?';
        $params[] = $filters['category'];
    }

    $whereSql = '';
    if ($conditions !== []) {
        $whereSql = ' WHERE ' . implode(' AND ', $conditions);
    }

    return [$whereSql, $params];
}

function admin_dashboard_report_rows(PDO $pdo, array $filters): array
{
    [$whereSql, $baseParams] = admin_dashboard_build_where($filters);

    $sql = 'SELECT r.id, r.created_at, r.status, r.category, r.amount '
        . 'FROM report_items AS r'
        . $whereSql
        . ' ORDER BY ' . $filters['sort_column'] . ' ' . $filters['sort_dir']
        . ' LIMIT ? OFFSET ?';

    $params = $baseParams;
    $params[] = $filters['limit'];
    $params[] = $filters['offset'];

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    return $stmt->fetchAll();
}

function admin_dashboard_report_summary(PDO $pdo, array $filters): array
{
    [$whereSql, $params] = admin_dashboard_build_where($filters);

    $sql = 'SELECT COUNT(*) AS total_rows, COALESCE(SUM(r.amount), 0) AS total_amount '
        . 'FROM report_items AS r'
        . $whereSql;

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $row = $stmt->fetch();
    return $row ?: ['total_rows' => 0, 'total_amount' => '0'];
}

function admin_dashboard_generate_report(PDO $pdo, array $post): array
{
    $filters = admin_dashboard_normalize_post_filters($post);
    return [
        'filters_applied' => $filters,
        'summary' => admin_dashboard_report_summary($pdo, $filters),
        'rows' => admin_dashboard_report_rows($pdo, $filters),
    ];
}

if (PHP_SAPI === 'cli' && realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    $dsn = getenv('MYSQL_DSN') ?: 'mysql:host=127.0.0.1;dbname=app;charset=utf8mb4';
    $user = getenv('MYSQL_USER') ?: 'root';
    $pass = getenv('MYSQL_PASS') ?: '';

    $pdo = create_mysql_pdo($dsn, $user, $pass);
    $demoPost = [
        'date_from' => date('Y-m-d', strtotime('-30 days')),
        'date_to' => date('Y-m-d'),
        'status' => 'all',
        'category' => 'all',
        'sort_by' => 'created_at',
        'sort_dir' => 'DESC',
        'limit' => 50,
        'offset' => 0,
    ];
    $report = admin_dashboard_generate_report($pdo, $demoPost);
    echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . PHP_EOL;
}