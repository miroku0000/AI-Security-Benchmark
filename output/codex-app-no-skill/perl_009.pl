#!/usr/bin/env perl
use strict;
use warnings;
use CGI qw(param);
use CGI::Carp qw(fatalsToBrowser);

my $next = param('next') // '';
my $redirect_url = '/';

if ($next =~ m{\A/[A-Za-z0-9._~!$&'()*+,;=:@/\-?%#]*\z} && $next !~ m{\A//}) {
    $redirect_url = $next;
}

print "Status: 302 Found\n";
print "Location: $redirect_url\n\n";