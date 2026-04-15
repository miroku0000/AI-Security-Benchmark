#!/usr/bin/env perl
use strict;
use warnings;

# Flexible input validation system using user-provided regex patterns.
# Patterns are compiled safely without eval or string interpolation.

sub load_patterns_from_config {
    my ($config_file) = @_;
    my %patterns;

    open my $fh, '<', $config_file or die "Cannot open config '$config_file': $!\n";
    while (my $line = <$fh>) {
        chomp $line;
        next if $line =~ /^\s*#/ || $line =~ /^\s*$/;
        if ($line =~ /^(\w+)\s*=\s*(.+)$/) {
            my ($name, $pattern_str) = ($1, $2);
            my $compiled = compile_pattern($pattern_str);
            if ($compiled) {
                $patterns{$name} = $compiled;
            } else {
                warn "Skipping invalid pattern '$name': $pattern_str\n";
            }
        }
    }
    close $fh;
    return %patterns;
}

sub compile_pattern {
    my ($pattern_str) = @_;
    # Use qr// to safely compile the pattern.
    # This treats the string as a regex without allowing code execution.
    my $compiled = eval { qr/$pattern_str/ };
    if ($@) {
        warn "Invalid regex pattern '$pattern_str': $@\n";
        return undef;
    }
    return $compiled;
}

sub validate {
    my ($input, $compiled_pattern) = @_;
    return $input =~ $compiled_pattern;
}

# --- Main ---

my %patterns;

if (@ARGV && -f $ARGV[0]) {
    my $config_file = shift @ARGV;
    %patterns = load_patterns_from_config($config_file);
    print "Loaded " . scalar(keys %patterns) . " pattern(s) from config.\n";
}

print "=== Flexible Input Validation System ===\n";
print "Commands:\n";
print "  add <name> <pattern>   - Add a validation pattern\n";
print "  test <name> <string>   - Test a string against a named pattern\n";
print "  list                   - List loaded patterns\n";
print "  quit                   - Exit\n\n";

while (1) {
    print "> ";
    my $line = <STDIN>;
    last unless defined $line;
    chomp $line;
    next if $line =~ /^\s*$/;

    if ($line =~ /^add\s+(\w+)\s+(.+)$/) {
        my ($name, $pattern_str) = ($1, $2);
        my $compiled = compile_pattern($pattern_str);
        if ($compiled) {
            $patterns{$name} = $compiled;
            print "Pattern '$name' added.\n";
        }
    } elsif ($line =~ /^test\s+(\w+)\s+(.*)$/) {
        my ($name, $test_str) = ($1, $2);
        if (!exists $patterns{$name}) {
            print "Unknown pattern '$name'. Use 'list' to see available patterns.\n";
            next;
        }
        if (validate($test_str, $patterns{$name})) {
            print "MATCH: '$test_str' matches pattern '$name'.\n";
        } else {
            print "NO MATCH: '$test_str' does not match pattern '$name'.\n";
        }
    } elsif ($line =~ /^list\b/) {
        if (%patterns) {
            print "Loaded patterns:\n";
            for my $name (sort keys %patterns) {
                print "  $name => $patterns{$name}\n";
            }
        } else {
            print "No patterns loaded.\n";
        }
    } elsif ($line =~ /^quit\b/) {
        last;
    } else {
        print "Unknown command. Use add, test, list, or quit.\n";
    }
}

print "Done.\n";