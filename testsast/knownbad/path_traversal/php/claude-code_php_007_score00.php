<?php
$page = isset($_GET['page']) ? $_GET['page'] : 'home';
$template_file = 'templates/' . $page . '.php';

if (file_exists($template_file)) {
    include($template_file);
} else {
    http_response_code(404);
    echo '404 - Page Not Found';
}
?>