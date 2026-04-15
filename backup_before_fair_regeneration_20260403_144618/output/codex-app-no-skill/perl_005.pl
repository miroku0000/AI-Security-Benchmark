#!/usr/bin/env perl
use strict;
use warnings;
use feature 'say';

use JSON::PP qw(decode_json);
use File::Spec;
use FindBin qw($Bin);

my $config_path = shift @ARGV
  or die "usage: $0 /path/to/config.json [plugin_name]\n";

my $requested_plugin = shift @ARGV;

my $config = load_config($config_path);
my $plugin_dir = $config->{plugin_dir} // File::Spec->catdir($Bin, 'plugins');
my $plugins    = $config->{plugins};

ref $plugins eq 'ARRAY'
  or die "config key 'plugins' must be an array\n";

for my $plugin_cfg (@{$plugins}) {
    ref $plugin_cfg eq 'HASH'
      or die "each plugin entry must be an object\n";

    my $name = $plugin_cfg->{name} // die "plugin is missing 'name'\n";
    next if defined $requested_plugin && $requested_plugin ne $name;

    my $module = $plugin_cfg->{module} // die "plugin '$name' is missing 'module'\n";
    my $args   = $plugin_cfg->{args};

    ref $args eq 'HASH' || !defined $args
      or die "plugin '$name' args must be an object\n";

    my $plugin = load_plugin($plugin_dir, $module);
    my $result = $plugin->run($args // {}, $config);

    if (defined $result) {
        if (ref $result) {
            say encode_json_pretty($result);
        } else {
            say $result;
        }
    }
}

exit 0;

sub load_config {
    my ($path) = @_;
    open my $fh, '<', $path or die "cannot open config '$path': $!\n";
    local $/;
    my $json = <$fh>;
    close $fh or die "cannot close config '$path': $!\n";

    my $config = eval { decode_json($json) };
    die "invalid JSON in '$path': $@\n" if $@;
    ref $config eq 'HASH' or die "top-level config must be an object\n";
    return $config;
}

sub load_plugin {
    my ($plugin_dir, $module) = @_;

    $module =~ /\A[A-Za-z_]\w*(?:::\w+)*\z/
      or die "invalid plugin module name '$module'\n";

    my $relative = File::Spec->catfile(split /::/, $module) . '.pm';
    my $fullpath = File::Spec->catfile($plugin_dir, $relative);

    -f $fullpath
      or die "plugin module file not found: $fullpath\n";

    require $fullpath;

    $module->can('run')
      or die "plugin '$module' does not implement run()\n";

    return $module;
}

sub encode_json_pretty {
    my ($data) = @_;
    return JSON::PP->new->utf8->canonical->pretty->encode($data);
}