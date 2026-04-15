if (@ARGV && $ARGV[0] eq '--config') {
    shift @ARGV;
    my $config_path = shift @ARGV or die "Usage: $0 [--config FILE] [strings...]\n";
    @patterns = load_patterns_from_file($config_path);
} elsif (@ARGV && $ARGV[0] eq '--pattern') {
    shift @ARGV;
    my $pattern = shift @ARGV or die "Usage: $0 [--pattern REGEX] [strings...]\n";
    @patterns = ($pattern);
} else {
    my $pattern = prompt("Enter regex pattern: ");
    @patterns = ($pattern);
}