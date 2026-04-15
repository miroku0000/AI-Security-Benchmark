#include "diagnostic_console.h"
#include "platform_hw.h"

int main(void)
{
    diagnostic_console_init();
    for (;;) {
        diagnostic_console_poll();
    }
    return 0;
}
