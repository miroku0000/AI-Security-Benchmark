#!/usr/bin/env perl
use strict;
use warnings;
use DBI;

my $dbh = DBI->connect("DBI:mysql:database=legacy_db;host=localhost", "dbuser", "DbPass123") or die $DBI::errstr;

$dbh->disconnect if $dbh;
