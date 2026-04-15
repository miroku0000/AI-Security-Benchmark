static void sleep_ms(unsigned int ms)
{
    clock_t start = clock();
    const clock_t wait_ticks = (clock_t)((double)ms * (double)CLOCKS_PER_SEC / 1000.0);
    while ((clock() - start) < wait_ticks)
    {
    }
}