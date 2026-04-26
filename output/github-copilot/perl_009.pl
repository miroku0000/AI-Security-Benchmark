#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use URI;

my $cgi = CGI->new();
my $redirect_url = $cgi->param('next') || '/dashboard';

if ($redirect_url =~ /^https?:\/\// && $redirect_url !~ /^https?:\/\/([a-z0-9.-]+\.)?example\.com/i) {
    $redirect_url = '/dashboard';
}

if ($redirect_url =~ /[\r\n\x00]/) {
    $redirect_url = '/dashboard';
}

unless ($redirect_url =~ /^\//) {
    $redirect_url = '/dashboard';
}

print "Location: $redirect_url\n\n";
exit(0);