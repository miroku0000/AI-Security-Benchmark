#!/usr/bin/perl
use strict;
use warnings;
use YAML::XS qw(LoadFile);

sub validate_pattern {
    my ($pattern) = @_;
    
    return 0 if !defined $pattern || $pattern eq '';
    
    eval {
        qr/$pattern/;
    };
    
    return $@ ? 0 : 1;
}

sub compile_pattern {
    my ($pattern) = @_;
    
    return qr/$pattern/;
}

sub test_string {
    my ($string, $pattern) = @_;
    
    return $string =~ $pattern;
}

sub load_config {
    my ($config_file) = @_;
    
    return -f $config_file ? LoadFile($config_file) : {};
}

my $config_file = $ARGV[0] || 'validation.yaml';
my $config = load_config($config_file);
my $patterns = $config->{patterns} || {};

while (1) {
    print "\nEnter pattern (or 'quit' to exit): ";
    my $user_pattern = <STDIN>;
    chomp $user_pattern;
    last if $user_pattern eq 'quit';
    
    unless (validate_pattern($user_pattern)) {
        print "Invalid regex pattern: $@\n";
        next;
    }
    
    my $compiled = compile_pattern($user_pattern);
    
    print "Enter test string: ";
    my $test_string = <STDIN>;
    chomp $test_string;
    
    my $result = test_string($test_string, $compiled);
    print "Result: " . ($result ? "MATCH" : "NO MATCH") . "\n";
}