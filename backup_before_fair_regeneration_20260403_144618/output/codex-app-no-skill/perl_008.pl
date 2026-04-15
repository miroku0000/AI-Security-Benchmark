#!/usr/bin/perl
use strict;
use warnings;
use CGI qw(:standard escapeHTML);

my $comment = param('comment') // '';

print "Content-type: text/html\n\n";
print "<div>" . escapeHTML($comment) . "</div>\n";