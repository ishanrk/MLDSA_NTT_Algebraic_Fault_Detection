#include "target.h"

#include <stdint.h>

int physical_dwt_init(void)
{
    volatile uint32_t *const demcr = (volatile uint32_t *)0xe000edfcU;
    volatile uint32_t *const ctrl = (volatile uint32_t *)0xe0001000U;
    volatile uint32_t *const count = (volatile uint32_t *)0xe0001004U;
    *demcr |= 1U << 24;
    if ((*ctrl & (1U << 25)) != 0U)
        return 0;
    *count = 0;
    *ctrl |= 1U;
    __asm volatile("dsb sy\nisb sy" ::: "memory");
    uint32_t before = *count;
    for (volatile unsigned i = 0; i < 1000U; i++) {
    }
    return (*ctrl & 1U) != 0U && *count != before;
}

uint32_t physical_cycles(void)
{
    __asm volatile("dsb sy\nisb sy" ::: "memory");
    uint32_t cycles = *(volatile uint32_t *)0xe0001004U;
    __asm volatile("" ::: "memory");
    return cycles;
}

__attribute__((naked)) uint32_t physical_stack_fill(void)
{
    __asm volatile(
        "mrs r0, msp\n"
        "ldr r1, =__stack_limit\n"
        "ldr r2, =0xa55aa55a\n"
        "1: cmp r1, r0\n"
        "bhs 2f\n"
        "str r2, [r1], #4\n"
        "b 1b\n"
        "2: bx lr\n");
}

__attribute__((naked)) uint32_t physical_stack_used(uint32_t start __attribute__((unused)))
{
    __asm volatile(
        "mov r1, r0\n"
        "ldr r0, =__stack_limit\n"
        "ldr r2, =0xa55aa55a\n"
        "1: cmp r0, r1\n"
        "bhs 2f\n"
        "ldr r3, [r0]\n"
        "cmp r3, r2\n"
        "bne 2f\n"
        "adds r0, #4\n"
        "b 1b\n"
        "2: ldr r1, =__stack_top\n"
        "subs r0, r1, r0\n"
        "bx lr\n");
}
