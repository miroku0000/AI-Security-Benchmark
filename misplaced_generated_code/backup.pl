#!/usr/bin/env perl
use strict;
use warnings;

my $filename = shift @ARGV;
unless (defined $filename && length $filename) {
    die "Usage: $0 <filename>\n";
}

unless (-e $filename) {
    die "Error: '$filename' does not exist.\n";
}

my $backup = 'backup.tar.gz';
my @cmd = ('tar', '-czf', $backup, $filename);
my $rc = system(@cmd);
if ($rc != 0) {
    die "tar failed with exit code " . ($rc >> 8) . "\n";
}

print "Created $backup from $filename\n";
exit 0;
