GetOptions(
    'pattern=s' => \$opt{pattern},
    'string=s'  => \$opt{string},
    'config=s'  => \$opt{config},
    'key=s'     => \$opt{key},
    'timeout=i' => \$opt{timeout},
    'help'      => \$opt{help},
) or usage();