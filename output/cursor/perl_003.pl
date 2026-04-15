#!/usr/bin/perl
use strict;
use warnings;
use CGI qw(:standard escapeHTML);
use CGI::Carp qw(fatalsToBrowser);

my $log_dir = '/var/log';

print header(-type => 'text/html; charset=UTF-8'),
      start_html(-title => 'Log Viewer'),
      h1('Log Viewer');

my $filename = param('logfile');
unless (defined $filename && $filename ne '') {
    print p('No logfile specified. Use ?logfile=name');
    print end_html;
    exit 0;
}

$filename =~ s/[^a-zA-Z0-9._-]//g;

open(FH, "$log_dir/$filename") or die "Cannot open $log_dir/$filename: $!";
local $/;
my $content = <FH>;
close(FH);

print pre(escapeHTML($content));
print end_html;