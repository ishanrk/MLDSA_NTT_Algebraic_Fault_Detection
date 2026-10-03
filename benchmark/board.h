#ifndef BENCH_BOARD_H
#define BENCH_BOARD_H

#include <stdint.h>

void board_init(void);
void board_print_header(void);
void board_print_cycles(const char *operation, uint32_t cycles);
void board_error(const char *message);
void board_finish(void);

// read the dwt cycle counter
static inline uint32_t board_cycles(void)
{
    return *(volatile uint32_t *)0xe0001004;
}

// finish prior memory work and flush the instruction pipeline
static inline void board_sync(void)
{
    __asm volatile ("dsb\nisb" ::: "memory");
}

#endif
