#!/usr/bin/perl
use strict;
use warnings;
use Cwd qw(abs_path);
use File::Basename;
use File::Spec;

# Plugin directory - only load from a trusted, controlled location
my $PLUGIN_DIR = abs_path(File::Spec->catdir(dirname(__FILE__), 'plugins'));

sub load_plugin {
    my ($plugin_name) = @_;

    # Validate plugin name to prevent path traversal
    if ($plugin_name !~ /^[a-zA-Z0-9_]+$/) {
        die "Invalid plugin name: '$plugin_name'. Only alphanumeric and underscores allowed.\n";
    }

    my $plugin_file = File::Spec->catfile($PLUGIN_DIR, "${plugin_name}.pm");
    my $resolved = abs_path($plugin_file);

    # Ensure the resolved path is still within the plugin directory
    if (!defined $resolved || index($resolved, $PLUGIN_DIR) != 0) {
        die "Plugin '$plugin_name' resolves outside the plugin directory.\n";
    }

    if (! -f $resolved) {
        die "Plugin file not found: $resolved\n";
    }

    # Check file ownership and permissions
    my @stat = stat($resolved);
    my $mode = $stat[2] & 07777;
    if ($mode & 0022) {
        die "Plugin '$plugin_name' is world/group writable (mode: " . sprintf("%04o", $mode) . "). Refusing to load.\n";
    }

    # Load the plugin as a Perl module via require (not eval on raw strings)
    my $package = "Plugin::${plugin_name}";
    require $resolved;

    # Verify the plugin implements the expected interface
    if (!$package->can('run')) {
        die "Plugin '$plugin_name' does not implement the required 'run' method.\n";
    }

    return $package;
}

sub run_plugin {
    my ($plugin_name, %args) = @_;
    my $package = load_plugin($plugin_name);
    return $package->run(%args);
}

# --- Main ---
if (!-d $PLUGIN_DIR) {
    mkdir $PLUGIN_DIR or die "Cannot create plugin directory: $!\n";
    print "Created plugin directory: $PLUGIN_DIR\n";
    print "Add .pm plugin modules there to extend functionality.\n";
    exit 0;
}

my $plugin_name = shift @ARGV;
if (!defined $plugin_name) {
    print "Usage: $0 <plugin_name> [key=value ...]\n";
    print "Plugins directory: $PLUGIN_DIR\n";

    opendir(my $dh, $PLUGIN_DIR) or die "Cannot open plugin directory: $!\n";
    my @plugins = grep { /\.pm$/ } readdir($dh);
    closedir($dh);

    if (@plugins) {
        print "Available plugins:\n";
        for my $p (sort @plugins) {
            $p =~ s/\.pm$//;
            print "  - $p\n";
        }
    } else {
        print "No plugins installed.\n";
    }
    exit 0;
}

# Parse key=value arguments
my %args;
for my $arg (@ARGV) {
    if ($arg =~ /^([^=]+)=(.*)$/) {
        $args{$1} = $2;
    }
}

my $result = run_plugin($plugin_name, %args);
print "Plugin result: $result\n" if defined $result;