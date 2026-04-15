#!/usr/bin/perl
use strict;
use warnings;
use CGI;

my $cgi = CGI->new;
my $redirect_url = $cgi->param('next');
$redirect_url = '/' unless defined $redirect_url && length $redirect_url;
print "Location: $redirect_url\n\n";