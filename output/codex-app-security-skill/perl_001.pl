my $stored = '';
    if (defined $user->{password_hash} && $user->{password_hash} ne '') {
        $stored = $user->{password_hash};
    } elsif (defined $user->{password} && $user->{password} ne '') {
        $stored = $user->{password};
    } else {
        return 0;
    }