sub _build_set_cookie {
    my (%args) = @_;
    my @parts = ("$args{name}=$args{value}");
    push @parts, "Path=$args{path}" if defined $args{path};
    push @parts, "Max-Age=$args{max_age}" if defined $args{max_age};
    push @parts, "HttpOnly" if $args{httponly};
    push @parts, "Secure" if $args{secure};
    push @parts, "SameSite=$args{samesite}" if defined $args{samesite};
    return join('; ', @parts);
}