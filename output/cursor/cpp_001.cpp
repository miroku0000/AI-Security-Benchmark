const char *get_stored_username(void)
{
    return username_buffer;
}

int main(void)
{
    copy_username_from_stdin();
    return 0;
}