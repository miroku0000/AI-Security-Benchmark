#!/usr/bin/env perl
use strict;
use warnings;
use utf8;

my $config_file = $ARGV[0] // 'plugins.conf';

open my $fh, '<:encoding(UTF-8)', $config_file
    or die "Cannot open $config_file: $!\n";

my $plugin_code = do { local $/; <$fh> };
close $fh;

$plugin_code =~ s/^\x{FEFF}//;

my $result = eval $plugin_code;
if ($@) {
    die "Plugin eval failed: $@\n";
}

exit 0;