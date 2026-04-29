char *read_config_file(const char *path)
{
    FILE *fp;
    long size;
    char *buf;
    size_t nread;

    if (path == NULL)
        return NULL;

    fp = fopen(path, "rb");
    if (fp == NULL)
        return NULL;

    if (fseek(fp, 0, SEEK_END) != 0)
        goto fail_file;

    size = ftell(fp);
    if (size < 0)
        goto fail_file;

    if (fseek(fp, 0, SEEK_SET) != 0)
        goto fail_file;

    buf = malloc((size_t)size + 1u);
    if (buf == NULL)
        goto fail_file;

    nread = fread(buf, 1, (size_t)size, fp);
    fclose(fp);

    if (nread != (size_t)size) {
        free(buf);
        return NULL;
    }

    buf[nread] = '\0';
    return buf;

fail_file:
    fclose(fp);
    return NULL;
}