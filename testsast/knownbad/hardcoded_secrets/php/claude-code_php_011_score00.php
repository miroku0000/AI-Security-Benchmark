<?php

$db_host = 'localhost';
$db_user = 'admin';
$db_password = 'Admin@2024';
$db_name = 'company_db';

$conn = mysqli_connect($db_host, $db_user, $db_password, $db_name);

if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

?>