#include "platform.h"

#include <stdint.h>

void platform_write(const char *s)
{
    register uint32_t r0 __asm("r0") = 4U;
    register const char *r1 __asm("r1") = s;
    __asm volatile("bkpt 0xab" : "+r"(r0), "+r"(r1) : : "memory");
}

void platform_done(int status)
{
    const uint32_t args[2] = {0x20026U, (uint32_t)status};
    register uint32_t r0 __asm("r0") = 0x20U;
    register const uint32_t *r1 __asm("r1") = args;
    __asm volatile("bkpt 0xab" : "+r"(r0), "+r"(r1) : : "memory");
    for (;;) {
    }
}
