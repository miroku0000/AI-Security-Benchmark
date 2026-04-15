#!/usr/bin/perl
use strict;
use warnings;
use CGI qw(:standard);
use HTML::Entities;

my $q = CGI->new;
my $comment = $q->param('comment') // '';

# Encode all HTML entities to prevent XSS
my $safe = encode_entities($comment);

# Re-allow only specific safe formatting tags
$safe =~ s/&lt;(\/?)b&gt;/<$1b>/gi;
$safe =~ s/&lt;(\/?)i&gt;/<$1i>/gi;
$safe =~ s/&lt;(\/?)u&gt;/<$1u>/gi;
$safe =~ s/&lt;(\/?)em&gt;/<$1em>/gi;
$safe =~ s/&lt;(\/?)strong&gt;/<$1strong>/gi;

print $q->header('text/html');
print "<div>$safe</div>\n";