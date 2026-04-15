#!/usr/bin/perl
use strict;
use warnings;
use CGI qw(:standard);

my $comment = param('comment') || '';
print "Content-type: text/html\n\n<div>$comment</div>";