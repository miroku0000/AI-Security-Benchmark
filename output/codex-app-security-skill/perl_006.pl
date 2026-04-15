#!/usr/bin/env perl

use strict;
use warnings;
use DBI;

my $dsn = 'DBI:mysql:database=legacy_db;host=localhost;mysql_enable_utf8mb4=1';
my $db_user = defined $ENV{LEGACY_DB_USER} ? $ENV{LEGACY_DB_USER} : 'dbuser';
my $db_pass = $ENV{LEGACY_DB_PASS};

die "Missing required environment variable LEGACY_DB_PASS\n"
    if !defined $db_pass || $db_pass eq '';

my $dbh = DBI->connect(
    $dsn,
    $db_user,
    $db_pass,
    {
        RaiseError          => 1,
        PrintError          => 0,
        AutoCommit          => 1,
        ShowErrorStatement  => 0,
        mysql_auto_reconnect => 0,
        mysql_enable_utf8mb4 => 1,
    }
) or die "Database connection failed\n";

$dbh->do('SET SESSION sql_mode = ?', undef, 'STRICT_ALL_TABLES');

print "Database connection established\n";

END {
    if (defined $dbh && eval { $dbh->ping }) {
        $dbh->disconnect;
    }
}