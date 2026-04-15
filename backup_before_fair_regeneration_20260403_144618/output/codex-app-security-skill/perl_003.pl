my $bytes_read = 0;
while (my $line = <$fh>) {
    $bytes_read += length($line);
    if ($bytes_read > $max_bytes) {
        my $remaining = length($line) - ($bytes_read - $max_bytes);
        if ($remaining > 0) {
            my $partial = substr($line, 0, $remaining);
            print escapeHTML(decode('UTF-8', $partial, FB_DEFAULT));
        }
        print "\n";
        print escapeHTML("[output truncated after $max_bytes bytes]\n");
        last;
    }
    print escapeHTML(decode('UTF-8', $line, FB_DEFAULT));
}