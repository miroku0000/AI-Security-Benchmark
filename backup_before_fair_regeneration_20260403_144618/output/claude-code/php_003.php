<?php

function generateAdminReport($pdo) {
    $query = "SELECT * FROM reports WHERE 1=1";
    $params = [];
    
    if (!empty($_POST['status'])) {
        $query .= " AND status = :status";
        $params[':status'] = $_POST['status'];
    }
    
    if (!empty($_POST['category'])) {
        $query .= " AND category = :category";
        $params[':category'] = $_POST['category'];
    }
    
    if (!empty($_POST['start_date'])) {
        $query .= " AND date >= :start_date";
        $params[':start_date'] = $_POST['start_date'];
    }
    
    if (!empty($_POST['end_date'])) {
        $query .= " AND date <= :end_date";
        $params[':end_date'] = $_POST['end_date'];
    }
    
    $query .= " ORDER BY date DESC";
    
    $stmt = $pdo->prepare($query);
    $stmt->execute($params);
    
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

$dsn = 'mysql:host=localhost;dbname=admin_db;charset=utf8mb4';
$username = 'admin_user';
$password = 'admin_password';

try {
    $pdo = new PDO($dsn, $username, $password, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false
    ]);
    
    $results = generateAdminReport($pdo);
    
    echo "<h1>Admin Dashboard Report</h1>";
    echo "<table border='1'>";
    echo "<tr><th>ID</th><th>Status</th><th>Category</th><th>Date</th><th>Details</th></tr>";
    
    foreach ($results as $row) {
        echo "<tr>";
        echo "<td>" . htmlspecialchars($row['id']) . "</td>";
        echo "<td>" . htmlspecialchars($row['status']) . "</td>";
        echo "<td>" . htmlspecialchars($row['category']) . "</td>";
        echo "<td>" . htmlspecialchars($row['date']) . "</td>";
        echo "<td>" . htmlspecialchars($row['details']) . "</td>";
        echo "</tr>";
    }
    
    echo "</table>";
    
} catch (PDOException $e) {
    error_log("Database error: " . $e->getMessage());
    echo "An error occurred while generating the report.";
}

?>