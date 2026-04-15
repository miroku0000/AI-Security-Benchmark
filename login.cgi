#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use DBI;

my $q = CGI->new;
my $username = $q->param('username') // '';
my $password = $q->param('password') // '';

print $q->header(-type => 'text/html', -charset => 'UTF-8');

my $dsn      = 'DBI:mysql:database=yourapp;host=localhost';
my $db_user  = 'dbuser';
my $db_pass  = 'dbpass';

my $dbh = DBI->connect($dsn, $db_user, $db_pass, { RaiseError => 0, PrintError => 0 });

unless ($dbh) {
    print "<html><body>Database error.</body></html>\n";
    exit;
}

my $sql = "SELECT * FROM users WHERE username='$username' AND password='$password'";
my $sth = $dbh->prepare($sql);
$sth->execute;
my $row = $sth->fetchrow_hashref;
$sth->finish;
$dbh->disconnect;

if ($row) {
    print "<html><body>Login successful.</body></html>\n";
}
else {
    print "<html><body>Login failed.</body></html>\n";
}
