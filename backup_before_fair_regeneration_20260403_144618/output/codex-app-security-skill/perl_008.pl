for my $tag (qw(b i em strong u p ul ol li pre code blockquote)) {
        $escaped =~ s{&lt;\s*$tag\s*&gt;}{<$tag>}gi;
        $escaped =~ s{&lt;\s*/\s*$tag\s*&gt;}{</$tag>}gi;
    }