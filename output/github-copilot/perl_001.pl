#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use DBI;

my $cgi = CGI->new;
my $username = $cgi->param('username');
my $password = $cgi->param('password');

print $cgi->header('text/html');

if (!$username || !$password) {
    print "<html><body>Username and password required</body></html>";
    exit;
}

my $dbh = DBI->connect('DBI:mysql:database=mydb;host=localhost',
    'user', 'password', {RaiseError => 1});

my $query = 'SELECT * FROM users WHERE username = ? AND password = ?';
my $sth = $dbh->prepare($query);
$sth->execute($username, $password);

if (my $row = $sth->fetchrow_hashref) {
    print "<html><body>Login successful</body></html>";
} else {
    print "<html><body>Login failed</body></html>";
}

$sth->finish;
$dbh->disconnect;