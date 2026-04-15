my $ref_type = ref $value;
    if ($ref_type eq 'ARRAY') {
        assert_safe_data($_, $seen) for @{$value};
        return;
    }
    if ($ref_type eq 'HASH') {
        for my $key (keys %{$value}) {
            $key =~ /\A[^\x00-\x1F\x7F]+\z/ or fail('plugin result contains an invalid hash key');
            assert_safe_data($value->{$key}, $seen);
        }
        return;
    }