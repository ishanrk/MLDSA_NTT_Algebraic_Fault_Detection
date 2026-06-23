#include "platform.h"

#include <stdio.h>

void platform_write(const char *s)
{
    fputs(s, stdout);
}
