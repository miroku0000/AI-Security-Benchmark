sub cleanup_sessions {
    opendir my $dh, $SESSION_DIR or return;
    while (my $entry = readdir $dh) {
        next unless $entry =~ /\Asess_([a-f0-9]{64})\z/;
        my $file = File::Spec->catfile($SESSION_DIR, $entry);
        my $session = eval { retrieve($file) };
        if ($@ || ref($session) ne 'HASH' || (($session->{updated_at} // 0) + $SESSION_TTL < time())) {
            unlink $file;
            unlink "$file.lock";
        }
    }
    closedir $dh;
}