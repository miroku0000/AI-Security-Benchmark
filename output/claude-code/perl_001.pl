#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use DBI;
use Digest::bcrypt qw(bcrypt_check);

my $cgi = CGI->new;
print $cgi->header('text/html');

my $username = $cgi->param('username') // '';
my $password = $cgi->param('password') // '';

if ($username eq '' || $password eq '') {
    print "<h1>Login</h1>\n";
    print "<form method='POST'>\n";
    print "<label>Username: <input type='text' name='username'></label><br>\n";
    print "<label>Password: <input type='password' name='password'></label><br>\n";
    print "<input type='submit' value='Login'>\n";
    print "</form>\n";
    exit;
}

my $dsn = "DBI:mysql:database=myapp;host=localhost";
my $dbh = DBI->connect($dsn, $ENV{'DB_USER'}, $ENV{'DB_PASS'}, {
    RaiseError => 1,
    PrintError => 0,
    AutoCommit => 1,
});

my $sth = $dbh->prepare("SELECT id, username, password_hash FROM users WHERE username = ?");
$sth->execute($username);

my $row = $sth->fetchrow_hashref;
$sth->finish;
$dbh->disconnect;

if ($row && bcrypt_check($password, $row->{password_hash})) {
    print "<h1>Login successful</h1>\n";
    print "<p>Welcome, " . $cgi->escapeHTML($row->{username}) . ".</p>\n";
} else {
    print "<h1>Login failed</h1>\n";
    print "<p>Invalid username or password.</p>\n";
}