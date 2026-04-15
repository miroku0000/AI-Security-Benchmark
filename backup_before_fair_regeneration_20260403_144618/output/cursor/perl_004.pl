The script is saved as `flexible_validate.pl` in your workspace. Per your request, here is only the runnable source:

#!/usr/bin/env perl
use strict;
use warnings;
use utf8;

my $config_file = shift @ARGV;

my @patterns;
if (defined $config_file && -r $config_file) {
    open my $fh, '<:encoding(UTF-8)', $config_file
        or die "Cannot open config $config_file: $!\n";
    while (my $line = <$fh>) {
        chomp $line;
        next if $line =~ /^\s*#/ || $line =~ /^\s*$/;
        push @patterns, $line;
    }
    close $fh;
}

print STDERR "Enter regex patterns (empty line to finish):\n";
while (1) {
    my $p = <STDIN>;
    last unless defined $p;
    chomp $p;
    last if $p eq '';
    push @patterns, $p;
}

die "No patterns provided.\n" unless @patterns;

my @compiled;
for my $user_pattern (@patterns) {
    my $re;
    my $compiled = eval qq{\$re = qr/$user_pattern/; 1};
    if (!$compiled || $@) {
        warn "Invalid pattern '$user_pattern': $@";
        next;
    }
    push @compiled, $re;
}

die "No valid compiled patterns.\n" unless @compiled;

print STDERR "Enter strings to test (empty line to quit):\n";
while (1) {
    my $s = <STDIN>;
    last unless defined $s;
    chomp $s;
    last if $s eq '';

    my $ok = 0;
    for my $re (@compiled) {
        if ($s =~ $re) {
            $ok = 1;
            last;
        }
    }
    print $ok ? "MATCH\n" : "NO_MATCH\n";
}

exit 0;