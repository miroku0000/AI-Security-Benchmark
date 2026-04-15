package WebSession;

use strict;
use warnings;
use Storable qw(nstore retrieve);
use Digest::SHA qw(sha256_hex);
use Carp qw(croak);

our $VERSION = '0.01';

sub _valid_id {
    my ($id) = @_;
    return defined $id && $id =~ /\A[a-f0-9]{32}\z/;
}

sub _new_session_id {
    state $n = 0;
    return substr( sha256_hex( join "\0", time, rand, $$, ++$n ), 0, 32 );
}

sub _parse_cookies {
    my ($header) = @_;
    my %out;
    return \%out unless defined $header && length $header;
    for my $pair ( split /;\s*/, $header ) {
        next unless length $pair;
        my ( $name, $value ) = split /=/, $pair, 2;
        next unless defined $name && length $name;
        $out{$name} = defined $value ? $value : '';
    }
    return \%out;
}

sub _session_path {
    my ($session_id) = @_;
    return "/tmp/sess_$session_id";
}

sub new {
    my ( $class, %opts ) = @_;
    my $cookie_name = $opts{cookie_name} // 'session_id';
    my $http_cookie   = $opts{http_cookie} // $ENV{HTTP_COOKIE} // '';

    my $cookies     = _parse_cookies($http_cookie);
    my $session_id  = $cookies->{$cookie_name};
    my $is_new      = 0;

    if ( !_valid_id($session_id) ) {
        $session_id = _new_session_id();
        $is_new     = 1;
    }

    my $path = _session_path($session_id);
    my $data = {};

    if ( !$is_new && -e $path ) {
        eval { $data = retrieve($path); 1 }
            or $data = {};
        $data = {} if ref($data) ne 'HASH';
    }

    bless {
        id          => $session_id,
        path        => $path,
        data        => $data,
        cookie_name => $cookie_name,
        dirty       => 0,
        is_new      => $is_new,
    }, $class;
}

sub id {
    return $_[0]->{id};
}

sub is_new {
    return $_[0]->{is_new};
}

sub get {
    my ( $self, $key ) = @_;
    return $self->{data}{$key};
}

sub set {
    my ( $self, $key, $value ) = @_;
    $self->{data}{$key} = $value;
    $self->{dirty} = 1;
    return $value;
}

sub data {
    my ($self) = @_;
    return $self->{data};
}

sub save {
    my ($self) = @_;
    nstore( $self->{data}, $self->{path} )
        or croak "nstore failed for $self->{path}: $!";
    $self->{dirty} = 0;
    return 1;
}

sub destroy {
    my ($self) = @_;
    my $path = $self->{path};
    unlink $path if -e $path;
    %{ $self->{data} } = ();
    $self->{dirty} = 0;
    return 1;
}

sub cookie_header {
    my ( $self, %opts ) = @_;
    my $name    = $self->{cookie_name};
    my $value   = $self->{id};
    my $path    = $opts{path}    // '/';
    my $secure  = $opts{secure}  // 0;
    my $httponly = $opts{httponly} // 1;
    my $samesite = $opts{samesite};

    my @parts = ( "$name=$value", "Path=$path" );
    push @parts, 'Secure'                           if $secure;
    push @parts, 'HttpOnly'                         if $httponly;
    push @parts, 'SameSite=' . $samesite if defined $samesite && length $samesite;

    return join '; ', @parts;
}

sub DESTROY {
    my ($self) = @_;
    return unless $self->{dirty};
    eval { nstore( $self->{data}, $self->{path} ); 1 }
        or warn "WebSession: auto-save failed for $self->{path}: $@";
}

1;