#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use DBI;
use Crypt::Eksblowfish::Bcrypt qw(bcrypt bcrypt_hash en_base64);
use Crypt::URandom qw(urandom);

my $cgi = CGI->new;
print $cgi->header('application/json');

my $action   = $cgi->param('action')   // '';
my $username = $cgi->param('username') // '';
my $password = $cgi->param('password') // '';

my $dbh = DBI->connect("dbi:mysql:dbname=myapp", "user", "pass",
    { RaiseError => 1, AutoCommit => 1 });

sub hash_password {
    my ($plain) = @_;
    my $salt = en_base64(urandom(16));
    my $settings = "\$2a\$12\$$salt";
    return bcrypt($plain, $settings);
}

sub verify_password {
    my ($plain, $stored_hash) = @_;
    return bcrypt($plain, $stored_hash) eq $stored_hash;
}

if ($action eq 'store') {
    my $hashed = hash_password($password);
    my $sth = $dbh->prepare("INSERT INTO users (username, password_hash) VALUES (?, ?)");
    $sth->execute($username, $hashed);
    print '{"status":"ok"}';
}
elsif ($action eq 'verify') {
    my $sth = $dbh->prepare("SELECT password_hash FROM users WHERE username = ?");
    $sth->execute($username);
    my ($stored) = $sth->fetchrow_array;

    if ($stored && verify_password($password, $stored)) {
        print '{"status":"authenticated"}';
    } else {
        print '{"status":"failed"}';
    }
}
else {
    print '{"status":"error","message":"invalid action"}';
}