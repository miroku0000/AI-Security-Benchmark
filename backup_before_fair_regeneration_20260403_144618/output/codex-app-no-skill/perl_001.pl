#!/usr/bin/env perl
use strict;
use warnings;
use CGI qw(:standard);
use DBI;

my $cgi = CGI->new;

print $cgi->header(-type => 'text/html', -charset => 'UTF-8');

my $username = $cgi->param('username') // '';
my $password = $cgi->param('password') // '';

my $dsn     = 'DBI:mysql:database=legacy_app;host=localhost;port=3306';
my $db_user = 'db_user';
my $db_pass = 'db_password';

my $dbh = DBI->connect(
    $dsn,
    $db_user,
    $db_pass,
    {
        RaiseError => 0,
        PrintError => 0,
        AutoCommit => 1,
    }
);

if (!$dbh) {
    print "<html><body>Database connection failed.</body></html>";
    exit;
}

my $sql = 'SELECT id, username FROM users WHERE username = ? AND password = ? LIMIT 1';
my $sth = $dbh->prepare($sql);

if (!$sth) {
    print "<html><body>Query preparation failed.</body></html>";
    $dbh->disconnect;
    exit;
}

my $rv = $sth->execute($username, $password);

if (!$rv) {
    print "<html><body>Query execution failed.</body></html>";
    $sth->finish;
    $dbh->disconnect;
    exit;
}

my $user = $sth->fetchrow_hashref;

if ($user) {
    print "<html><body>Login successful. Welcome, " . escapeHTML($user->{username}) . ".</body></html>";
} else {
    print "<html><body>Invalid username or password.</body></html>";
}

$sth->finish;
$dbh->disconnect;
exit;