#include "core.h"

#include <stdint.h>

extern uint32_t __stack_limit;

int platform_dwt_init(void)
{
    volatile uint32_t *const demcr = (volatile uint32_t *)0xe000edfcU;
    volatile uint32_t *const ctrl = (volatile uint32_t *)0xe0001000U;
    volatile uint32_t *const count = (volatile uint32_t *)0xe0001004U;

    *demcr |= 1U << 24;
    if ((*ctrl & (1U << 25)) != 0U)
        return 0;
    *count = 0;
    *ctrl |= 1U;
    if ((*ctrl & 1U) == 0U)
        return 0;
    for (volatile unsigned i = 0; i < 1000U; i++) {
    }
    return *count != 0U;
}

uint32_t platform_cycles(void)
{
    return *(volatile uint32_t *)0xe0001004U;
}

uint32_t platform_stack_fill(void)
{
    uint32_t sp;
    __asm volatile("mrs %0, msp" : "=r"(sp));
    for (uint32_t *p = &__stack_limit; (uintptr_t)p < (uintptr_t)sp; p++)
        *p = 0xa55aa55aU;
    __asm volatile("" ::: "memory");
    return sp;
}

uint32_t platform_stack_used(uint32_t start)
{
    uint32_t *p = &__stack_limit;
    while ((uintptr_t)p < (uintptr_t)start && *p == 0xa55aa55aU)
        p++;
    return start - (uint32_t)(uintptr_t)p;
}
