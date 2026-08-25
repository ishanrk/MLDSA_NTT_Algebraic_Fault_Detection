#include "platform.h"
#include "target.h"

#include <stdint.h>

extern uint32_t __data_load, __data_start, __data_end;
extern uint32_t __bss_start, __bss_end;
extern int main(void);

void Reset_Handler(void);

void Reset_Handler(void)
{
    __asm volatile("cpsid i" ::: "memory");
    *(volatile uint32_t *)0xe000ed08U = 0x08000000U;
    uint32_t *src = &__data_load;
    for (uint32_t *p = &__data_start; p < &__data_end; p++)
        *p = *src++;
    for (uint32_t *p = &__bss_start; p < &__bss_end; p++)
        *p = 0;
    physical_init();
    platform_done(main());
}
