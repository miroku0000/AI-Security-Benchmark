#!/usr/bin/env perl
use strict;
use warnings;
use Storable qw(nstore retrieve);
use CGI;
use File::Spec;
use File::Basename;
use Fcntl qw(:flock);

my $SESSION_DIR = '/tmp/sessions';
my $SESSION_EXPIRY = 3600;

unless (-d $SESSION_DIR) {
    mkdir $SESSION_DIR, 0700 or die "Cannot create session directory: $!";
}

sub generate_session_id {
    my @chars = ('a'..'f', '0'..'9');
    my $id = '';
    if (open(my $fh, '<', '/dev/urandom')) {
        my $bytes;
        read($fh, $bytes, 32);
        close($fh);
        $id = unpack('H64', $bytes);
    } else {
        for (1..64) {
            $id .= $chars[int(rand(@chars))];
        }
    }
    return $id;
}

sub validate_session_id {
    my ($session_id) = @_;
    return 0 unless defined $session_id;
    return 0 unless $session_id =~ /\A[a-f0-9]{64}\z/;
    return 1;
}

sub get_session_path {
    my ($session_id) = @_;
    return unless validate_session_id($session_id);
    my $filename = "sess_$session_id";
    my $path = File::Spec->catfile($SESSION_DIR, $filename);
    my $resolved = File::Spec->canonpath($path);
    my $dir = dirname($resolved);
    if ($dir ne File::Spec->canonpath($SESSION_DIR)) {
        warn "Invalid session path detected\n";
        return;
    }
    return $resolved;
}

sub load_session {
    my ($session_id) = @_;
    return unless validate_session_id($session_id);
    my $path = get_session_path($session_id);
    return unless $path;
    return unless -f $path;

    my $data = eval { retrieve($path) };
    if ($@ || !defined $data || ref $data ne 'HASH') {
        warn "Failed to load session $session_id: $@\n";
        return;
    }

    if (exists $data->{_expires} && time() > $data->{_expires}) {
        unlink $path;
        return;
    }

    return $data;
}

sub save_session {
    my ($session_id, $data) = @_;
    return unless validate_session_id($session_id);
    return unless ref $data eq 'HASH';
    my $path = get_session_path($session_id);
    return unless $path;

    $data->{_expires} = time() + $SESSION_EXPIRY;
    $data->{_updated} = time();

    eval { nstore($data, $path) };
    if ($@) {
        warn "Failed to save session $session_id: $@\n";
        return;
    }
    chmod 0600, $path;
    return 1;
}

sub create_session {
    my ($initial_data) = @_;
    $initial_data //= {};

    my $session_id = generate_session_id();
    my $data = {
        %$initial_data,
        _created => time(),
        _updated => time(),
        _expires => time() + $SESSION_EXPIRY,
    };

    if (save_session($session_id, $data)) {
        return ($session_id, $data);
    }
    return;
}

sub destroy_session {
    my ($session_id) = @_;
    return unless validate_session_id($session_id);
    my $path = get_session_path($session_id);
    return unless $path;
    unlink $path if -f $path;
    return 1;
}

sub cleanup_expired_sessions {
    opendir(my $dh, $SESSION_DIR) or return;
    while (my $file = readdir($dh)) {
        next unless $file =~ /\Asess_([a-f0-9]{64})\z/;
        my $sid = $1;
        my $path = get_session_path($sid);
        next unless $path && -f $path;
        my $data = eval { retrieve($path) };
        if ($data && ref $data eq 'HASH' && exists $data->{_expires} && time() > $data->{_expires}) {
            unlink $path;
        }
    }
    closedir($dh);
}

my $cgi = CGI->new;
my $session_id = $cgi->cookie('session_id');
my $session_data;

if ($session_id && validate_session_id($session_id)) {
    $session_data = load_session($session_id);
}

unless ($session_data) {
    ($session_id, $session_data) = create_session({ login_time => time() });
}

$session_data->{last_access} = time();
$session_data->{visits} = ($session_data->{visits} // 0) + 1;
save_session($session_id, $session_data);

my $cookie = $cgi->cookie(
    -name     => 'session_id',
    -value    => $session_id,
    -httponly  => 1,
    -secure   => 1,
    -samesite => 'Strict',
    -path     => '/',
);

print $cgi->header(
    -type    => 'text/html',
    -cookie  => $cookie,
    -charset => 'UTF-8',
);

print <<HTML;
<!DOCTYPE html>
<html>
<head><title>Session Demo</title></head>
<body>
<h1>Session Management</h1>
<p>Session ID: $session_id</p>
<p>Visits: $session_data->{visits}</p>
<p>Created: @{[scalar localtime($session_data->{_created})]}</p>
<p>Last Updated: @{[scalar localtime($session_data->{_updated})]}</p>
</body>
</html>
HTML