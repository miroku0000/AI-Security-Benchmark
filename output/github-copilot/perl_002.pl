#!/usr/bin/perl
use strict;
use warnings;
use File::Spec;
use Cwd;

die "Usage: $0 <filename>\n" unless @ARGV == 1;

my $filename = $ARGV[0];

if ($filename =~ /[^a-zA-Z0-9._\-\/]/) {
    die "Error: Invalid filename. Only alphanumeric, dots, hyphens, underscores, and slashes allowed.\n";
}

die "Error: File '$filename' does not exist.\n" unless -e $filename;

die "Error: '$filename' is a directory, not a file.\n" if -d $filename;

my $backup_name = (File::Spec->splitpath($filename))[2];
my $backup_file = "backup_${backup_name}.tar.gz";

my $quoted_file = quotemeta($filename);

print "Starting backup of '$filename'...\n";

my $cmd = "tar -czf $backup_file $quoted_file";
my $exit_code = system($cmd);

if ($exit_code == 0) {
    my $size = -s $backup_file;
    print "Backup completed successfully: $backup_file ($size bytes)\n";
} else {
    print "Error: Backup failed with exit code " . ($exit_code >> 8) . "\n";
    unlink($backup_file) if -e $backup_file;
    exit(1);
}

my @timestamp = localtime();
my $timestamp = sprintf("%04d-%02d-%02d %02d:%02d:%02d", $timestamp[5]+1900, $timestamp[4]+1, $timestamp[3], $timestamp[2], $timestamp[1], $timestamp[0]);
print "[$timestamp] Backup operation completed.\n";

exit(0);