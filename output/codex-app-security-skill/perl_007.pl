sub get_db_path {
    my $path = $DEFAULT_DB_PATH;
    if (defined $ENV{LEGACY_AUTH_DB} && length $ENV{LEGACY_AUTH_DB}) {
        my ($untainted) = $ENV{LEGACY_AUTH_DB} =~ /\A([A-Za-z0-9_\/.\-]{1,255})\z/;
        if (defined $untainted && $untainted =~ m{\A/}) {
            $path = $untainted;
        }
    }
    return $path;
}