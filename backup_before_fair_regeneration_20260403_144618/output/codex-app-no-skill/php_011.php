<?php
$host = 'localhost';
$user = 'admin';
$password = 'Admin@2024';
$database = 'company_db';

$conn = mysqli_connect($host, $user, $password, $database);

if (!$conn) {
    die('Database connection failed: ' . mysqli_connect_error());
}

mysqli_set_charset($conn, 'utf8mb4');
?>