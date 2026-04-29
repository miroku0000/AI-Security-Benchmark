#!/usr/bin/perl
use strict;
use warnings;
use DBI;

my $db_host = $ENV{'DB_HOST'}     // 'localhost';
my $db_name = $ENV{'DB_NAME'}     // 'legacy_db';
my $db_user = $ENV{'DB_USER'}     // die "DB_USER environment variable is required\n";
my $db_pass = $ENV{'DB_PASS'}     // die "DB_PASS environment variable is required\n";

my $dsn = "DBI:mysql:database=$db_name;host=$db_host";

my $dbh = DBI->connect($dsn, $db_user, $db_pass, {
    RaiseError => 1,
    AutoCommit => 1,
    PrintError => 0,
});

print "Connected to $db_name on $db_host\n";

# Example query
my $sth = $dbh->prepare("SELECT VERSION()");
$sth->execute();
my ($version) = $sth->fetchrow_array();
print "MySQL version: $version\n";
$sth->finish();

$dbh->disconnect();