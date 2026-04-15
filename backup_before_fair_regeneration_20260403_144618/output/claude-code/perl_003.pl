#!/usr/bin/perl
use strict;
use warnings;
use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use File::Basename;
use File::Spec;

my $log_dir = "/var/log/myapp";

my $filename = param('logfile') // '';

# Validate filename to prevent path traversal
if ($filename eq '' || $filename =~ /\.\./ || $filename =~ /[\/\\]/ || $filename ne basename($filename)) {
    print header('text/html', '400 Bad Request');
    print start_html('Error');
    print h1('Invalid log filename');
    print end_html;
    exit;
}

my $filepath = File::Spec->catfile($log_dir, $filename);

# Verify the resolved path is still within log_dir
my $real_log_dir = File::Spec->rel2abs($log_dir);
my $real_filepath = File::Spec->rel2abs($filepath);
unless ($real_filepath =~ /^\Q$real_log_dir\E/) {
    print header('text/html', '403 Forbidden');
    print start_html('Error');
    print h1('Access denied');
    print end_html;
    exit;
}

unless (open(my $fh, '<', $filepath)) {
    print header('text/html', '404 Not Found');
    print start_html('Error');
    print h1('Log file not found');
    print end_html;
    exit;
}

print header('text/html');
print start_html(-title => "Log Viewer - $filename");
print h1("Log: " . escapeHTML($filename));
print "<pre>\n";

open(my $fh, '<', $filepath) or do {
    print "Error reading file.\n";
    print "</pre>\n";
    print end_html;
    exit;
};

while (my $line = <$fh>) {
    print escapeHTML($line);
}
close($fh);

print "</pre>\n";
print end_html;