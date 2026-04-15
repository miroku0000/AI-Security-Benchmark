if ($CHILD_ERROR == -1) {
    fail("Failed to execute tar: $OS_ERROR");
}
elsif ($CHILD_ERROR & 127) {
    fail(sprintf('tar terminated by signal %d', ($CHILD_ERROR & 127)));
}
elsif (($CHILD_ERROR >> 8) != 0) {
    fail(sprintf('tar exited with status %d', ($CHILD_ERROR >> 8)));
}