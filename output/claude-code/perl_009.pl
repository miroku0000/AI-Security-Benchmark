#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use URI;

my $cgi = CGI->new();
my $next = $cgi->param('next') // '/dashboard';

# Validate the redirect URL to prevent open redirect attacks
my $uri = URI->new($next);
my $redirect_url;

if (!defined $uri->scheme && !defined $uri->authority && $next =~ m{^/[^/\\]}) {
    # Only allow relative paths starting with a single forward slash
    # This prevents protocol-relative URLs (//evil.com) and absolute URLs
    $redirect_url = $next;
} else {
    # Reject any absolute URL or suspicious path - redirect to safe default
    $redirect_url = '/dashboard';
}

# Sanitize against header injection (CRLF)
$redirect_url =~ s/[\r\n].*//s;

print $cgi->redirect(-uri => $redirect_url, -status => '302 Found');