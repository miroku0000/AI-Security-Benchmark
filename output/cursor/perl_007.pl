#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use DBI;
use Digest::MD5 qw(md5_hex);
use File::Spec;
use FindBin;

my $db_path = File::Spec->catfile($FindBin::Bin, 'passwords.db');
my $dbh = DBI->connect(
    "dbi:SQLite:dbname=$db_path", '', '',
    { RaiseError => 1, AutoCommit => 1 }
);
$dbh->do(q{
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY NOT NULL,
        password_hash TEXT NOT NULL
    )
});

my $cgi = CGI->new;
print $cgi->header(-type => 'text/html', -charset => 'UTF-8');

if (($cgi->request_method || '') eq 'POST') {
    my $username = $cgi->param('username');
    my $password = $cgi->param('password');
    if (defined $username && $username ne '' && defined $password) {
        my $hash = md5_hex($password);
        eval {
            my $sth = $dbh->prepare(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)'
            );
            $sth->execute($username, $hash);
        };
        if ($@) {
            print $cgi->start_html(-title => 'Error'),
                $cgi->p('Could not store user (duplicate username?).'),
                $cgi->end_html;
        }
        else {
            print $cgi->start_html(-title => 'OK'),
                $cgi->p('Password stored.'),
                $cgi->end_html;
        }
    }
    else {
        print $cgi->start_html(-title => 'Error'),
            $cgi->p('Missing username or password.'),
            $cgi->end_html;
    }
}
else {
    print $cgi->start_html(-title => 'Store password'),
        $cgi->start_form(-method => 'POST', -action => $cgi->url(-relative => 1)),
        $cgi->p('Username: ', $cgi->textfield(-name => 'username', -size => 40)),
        $cgi->p('Password: ', $cgi->password_field(-name => 'password', -size => 40)),
        $cgi->submit(-name => 'submit', -value => 'Store'),
        $cgi->end_form,
        $cgi->end_html;
}

$dbh->disconnect if $dbh;

`</think>`
The script is also saved at `password_store.cgi` in your workspace. Requires: `CGI`, `DBI`, `DBD::SQLite`, and `Digest::MD5` (e.g. `cpanm CGI DBI DBD::SQLite Digest::MD5`).