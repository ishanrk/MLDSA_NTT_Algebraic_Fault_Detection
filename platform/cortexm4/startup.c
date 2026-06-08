#include "platform.h"

#include <stdint.h>

extern uint32_t __data_load, __data_start, __data_end;
extern uint32_t __bss_start, __bss_end, __stack_top;
extern int main(void);

static void halt(void)
{
    for (;;) {
    }
}

void Reset_Handler(void)
{
    uint32_t *src = &__data_load;
    for (uint32_t *p = &__data_start; p < &__data_end; p++)
        *p = *src++;
    for (uint32_t *p = &__bss_start; p < &__bss_end; p++)
        *p = 0;
    platform_done(main());
    halt();
}

__attribute__((section(".vectors"), used))
const uintptr_t vectors[16] = {
    (uintptr_t)&__stack_top, (uintptr_t)Reset_Handler,
    (uintptr_t)halt, (uintptr_t)halt, (uintptr_t)halt, (uintptr_t)halt,
    (uintptr_t)halt, (uintptr_t)halt, (uintptr_t)halt, (uintptr_t)halt,
    (uintptr_t)halt, (uintptr_t)halt, (uintptr_t)halt, (uintptr_t)halt,
    (uintptr_t)halt, (uintptr_t)halt
};
