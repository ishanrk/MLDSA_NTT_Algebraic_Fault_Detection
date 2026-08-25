#include "platform.h"
#include "target.h"

#include <stdint.h>

extern uint32_t __stack_top;

__attribute__((noinline)) static void burn_stack(void)
{
    volatile uint32_t words[256];
    for (unsigned i = 0; i < 256; i++)
        words[i] = i + 1U;
    __asm volatile("" : : "r"(words) : "memory");
}

int main(void)
{
    uint32_t mark = physical_stack_fill();
    uint32_t base = physical_stack_used(mark);
    if (base != (uint32_t)(uintptr_t)&__stack_top - mark)
        return 1;
    mark = physical_stack_fill();
    burn_stack();
    uint32_t used = physical_stack_used(mark);
    if (used < base + 1024U)
        return 2;
    if (physical_dwt_init())
        return 3;
    platform_write("CORE total stack watermark PASS\nCORE unavailable DWT PASS\n");
    return 0;
}
