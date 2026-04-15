#!/usr/bin/env perl
use strict;
use warnings;
use File::Basename;
use File::Spec;

die "Usage: $0 <filename>\n" unless @ARGV == 1;

my $filename = $ARGV[0];

# Validate the file exists
die "Error: File '$filename' does not exist.\n" unless -e $filename;
die "Error: '$filename' is not a regular file.\n" unless -f $filename;

# Resolve to absolute path and validate no path traversal
my $abs_path = File::Spec->rel2abs($filename);
my $basename = fileparse($abs_path);

# Reject filenames with characters that could cause shell issues
if ($basename =~ /[^a-zA-Z0-9._\-]/) {
    die "Error: Filename contains disallowed characters. Use alphanumeric, dot, hyphen, or underscore only.\n";
}

my $backup_name = "backup_${basename}.tar.gz";

# Use list form of system() to avoid shell interpolation entirely
my @cmd = ('tar', '-czf', $backup_name, $abs_path);

print "Backing up '$abs_path' to '$backup_name'...\n";

my $exit_code = system(@cmd);

if ($exit_code == 0) {
    print "Backup created successfully: $backup_name\n";
} else {
    my $status = $exit_code >> 8;
    die "Error: tar exited with status $status\n";
}