#!/usr/bin/perl
use strict;
use warnings;
use CGI qw(:standard escapeHTML);
use File::Spec;

my $q = CGI->new;
my $log_dir = '/var/log/myapp';
my $filename = $q->param('logfile') // '';

print $q->header(-type => 'text/html', -charset => 'UTF-8');
print "<!DOCTYPE html><html><head><title>Log Viewer</title></head><body>";

if ($filename eq '') {
    print "<h1>Log Viewer</h1><p>Missing logfile parameter.</p></body></html>";
    exit;
}

if ($filename !~ /\A[\w.\-]+\z/) {
    print "<h1>Log Viewer</h1><p>Invalid logfile parameter.</p></body></html>";
    exit;
}

my $path = File::Spec->catfile($log_dir, $filename);

unless (-f $path && -r $path) {
    print "<h1>Log Viewer</h1><p>Log file not found or not readable.</p></body></html>";
    exit;
}

open(my $fh, '<', $path) or do {
    print "<h1>Log Viewer</h1><p>Unable to open log file.</p></body></html>";
    exit;
};

print "<h1>Viewing " . escapeHTML($filename) . "</h1><pre>";
while (my $line = <$fh>) {
    print escapeHTML($line);
}
close($fh);

print "</pre></body></html>";