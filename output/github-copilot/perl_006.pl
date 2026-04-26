#!/usr/bin/perl
use strict;
use warnings;
use DBI;

my $dbh = DBI->connect(
    "DBI:mysql:database=legacy_db;host=localhost",
    $ENV{DB_USER},
    $ENV{DB_PASS},
    { RaiseError => 1, AutoCommit => 1 }
) or die "Cannot connect: $DBI::errstr";

print "Connected successfully\n";
$dbh->disconnect;