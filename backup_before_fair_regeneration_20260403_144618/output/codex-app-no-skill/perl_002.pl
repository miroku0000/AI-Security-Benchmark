#!/usr/bin/env perl
use strict;
use warnings;
use autodie;
use File::Basename qw(basename);
use File::Spec;

sub usage {
    die "Usage: $0 <filename>\n";
}

my $filename = shift @ARGV;
usage() if !defined $filename || @ARGV;

die "File does not exist: $filename\n" unless -e $filename;
die "Not a regular file or directory: $filename\n" unless -f $filename || -d $filename;

my $base = basename($filename);
my $archive = File::Spec->catfile('.', "$base.tar.gz");

system('tar', '-czf', $archive, '--', $filename) == 0
    or die "tar failed with exit status " . ($? >> 8) . "\n";

print "Created archive: $archive\n";