#!/usr/bin/env perl
use strict;
use warnings;
use DBI;

my $dsn  = $ENV{LEGACY_DB_DSN}  // 'DBI:mysql:database=legacy_db;host=localhost';
my $user = $ENV{LEGACY_DB_USER} // 'dbuser';
my $pass = $ENV{LEGACY_DB_PASS} // die "Set LEGACY_DB_PASS in the environment\n";

my $dbh = DBI->connect(
    $dsn,
    $user,
    $pass,
    {
        RaiseError => 1,
        PrintError => 0,
        AutoCommit => 1,
        mysql_enable_utf8 => 1,
    }
) or die "Database connection failed: $DBI::errstr\n";

print "Connected successfully\n";

END {
    if (defined $dbh) {
        $dbh->disconnect;
    }
}