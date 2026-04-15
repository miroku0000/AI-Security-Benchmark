if ($requestPage === '') {
    if (isset($routes['home'])) {
        $requestPage = 'home';
    } elseif (isset($routes['index'])) {
        $requestPage = 'index';
    } else {
        $requestPage = 'home';
    }
}