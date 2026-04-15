#!/usr/bin/env perl
use strict;
use warnings;
use CGI qw();

my $cgi = CGI->new;

sub safe_redirect_target {
    my ($value) = @_;
    my $default = '/';

    return $default if !defined $value;

    $value =~ s/^\s+//;
    $value =~ s/\s+\z//;

    return $default if $value eq '';
    return $default if length($value) > 2048;

    # Prevent header injection and other control-character abuse.
    return $default if $value =~ /[\x00-\x1F\x7F]/;

    # Only allow site-local absolute paths.
    return $default if $value =~ m{\A//};
    return $default if $value =~ /\A[A-Za-z][A-Za-z0-9+.\-]*:/;
    return $default if $value !~ m{\A/};
    return $default if $value =~ /\\/;

    return $value;
}

my $redirect_url = safe_redirect_target( scalar $cgi->param('next') );

print "Status: 302 Found\r\n";
print "Location: $redirect_url\r\n";
print "Cache-Control: no-store\r\n";
print "Pragma: no-cache\r\n";
print "Content-Length: 0\r\n";
print "\r\n";