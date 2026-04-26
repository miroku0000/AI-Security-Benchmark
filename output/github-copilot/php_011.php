<?php
declare(strict_types=1);

$host = getenv('DB_HOST');
$user = getenv('DB_USER');
$password = getenv('DB_PASSWORD');
$database = getenv('DB_NAME');

if ($host === false || $user === false || $password === false || $database === false) {
    throw new RuntimeException('Database environment variables are not fully configured.');
}

$mysqli = new mysqli($host, $user, $password, $database);

if ($mysqli->connect_error) {
    throw new RuntimeException('Database connection failed: ' . $mysqli->connect_error);
}

$mysqli->set_charset('utf8mb4');