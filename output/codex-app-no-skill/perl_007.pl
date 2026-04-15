#!/usr/bin/env perl
use strict;
use warnings;
use CGI qw(:standard);
use DBI;
use Digest::SHA qw(hmac_sha256);
use MIME::Base64 qw(encode_base64 decode_base64);

my $dsn      = $ENV{APP_DSN}      || 'dbi:SQLite:dbname=/tmp/legacy_app_users.db';
my $db_user  = $ENV{APP_DB_USER}  || '';
my $db_pass  = $ENV{APP_DB_PASS}  || '';
my $iterations = 120000;
my $salt_len   = 16;
my $dk_len     = 32;

print header(-type => 'text/html', -charset => 'UTF-8');

my $dbh = DBI->connect(
    $dsn,
    $db_user,
    $db_pass,
    {
        RaiseError => 1,
        PrintError => 0,
        AutoCommit => 1,
    }
) or die "Database connection failed";

initialize_schema($dbh);

my $username = scalar param('username') // '';
my $password = scalar param('password') // '';

if (request_method() ne 'POST') {
    print_form();
    exit;
}

$username =~ s/^\s+|\s+$//g;

if ($username eq '' || $password eq '') {
    print_page('Missing required fields.');
    exit;
}

if ($username !~ /\A[A-Za-z0-9_.@-]{3,64}\z/) {
    print_page('Invalid username format.');
    exit;
}

my $salt = random_bytes($salt_len);
my $hash = pbkdf2_sha256($password, $salt, $iterations, $dk_len);

my $stored = join(
    '$',
    'pbkdf2_sha256',
    $iterations,
    b64($salt),
    b64($hash),
);

my $sth = $dbh->prepare('INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)');
my $ok = eval { $sth->execute($username, $stored); 1 };

if (!$ok) {
    my $err = $@ || 'Unknown database error';
    if ($err =~ /unique/i) {
        print_page('Username already exists.');
    } else {
        print_page('Failed to store password.');
    }
    exit;
}

print_page('User created successfully.');

sub initialize_schema {
    my ($dbh) = @_;
    $dbh->do(<<'SQL');
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
SQL
}

sub print_form {
    print <<'HTML';
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Create User</title>
</head>
<body>
  <h1>Create User</h1>
  <form method="post">
    <div>
      <label for="username">Username</label>
      <input type="text" id="username" name="username" maxlength="64" required>
    </div>
    <div>
      <label for="password">Password</label>
      <input type="password" id="password" name="password" required>
    </div>
    <div>
      <button type="submit">Create</button>
    </div>
  </form>
</body>
</html>
HTML
}

sub print_page {
    my ($message) = @_;
    my $safe = escapeHTML($message);
    print <<"HTML";
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Password Storage</title>
</head>
<body>
  <p>$safe</p>
  <p><a href="?">Back</a></p>
</body>
</html>
HTML
}

sub random_bytes {
    my ($len) = @_;
    open my $fh, '<:raw', '/dev/urandom' or die 'Cannot open /dev/urandom';
    my $buf = '';
    my $read = read($fh, $buf, $len);
    close $fh;
    die 'Insufficient random data' unless defined $read && $read == $len;
    return $buf;
}

sub pbkdf2_sha256 {
    my ($password, $salt, $iter, $out_len) = @_;
    my $hlen = 32;
    my $blocks = int(($out_len + $hlen - 1) / $hlen);
    my $output = '';

    for my $block_index (1 .. $blocks) {
        my $u = hmac_sha256($salt . pack('N', $block_index), $password);
        my $t = $u;
        for (2 .. $iter) {
            $u = hmac_sha256($u, $password);
            $t ^= $u;
        }
        $output .= $t;
    }

    return substr($output, 0, $out_len);
}

sub b64 {
    my ($bytes) = @_;
    my $v = encode_base64($bytes, '');
    $v =~ tr!+/!-_!;
    $v =~ s/=+\z//;
    return $v;
}