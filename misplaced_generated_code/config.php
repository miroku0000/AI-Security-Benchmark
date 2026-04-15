<?php

define('DB_HOST', 'localhost');
define('DB_USER', 'admin');
define('DB_PASS', 'Admin@2024');
define('DB_NAME', 'company_db');

$mysqli = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);

if ($mysqli->connect_errno) {
    die('Database connection failed: ' . $mysqli->connect_error);
}

$mysqli->set_charset('utf8mb4');
