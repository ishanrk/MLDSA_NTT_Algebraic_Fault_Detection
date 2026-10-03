#include "board.h"
#include <stddef.h>

#define REG(addr) (*(volatile uint32_t *)(addr))

#ifdef MLDSA_BLOCK_CHECKER
#define VARIANT "guarded"
#else
#define VARIANT "plain"
#endif

extern uint32_t _estack, _sidata, _sdata, _edata, _sbss, _ebss;
int main(void);

/* no standard c runtime */
void *memcpy(void *dst, const void *src, size_t len)
{
    uint8_t *d = dst;
    const uint8_t *s = src;
    for (size_t i = 0; i < len; i++)
    {
        d[i] = s[i];
    }
    return dst;
}

void *memset(void *dst, int value, size_t len)
{
    uint8_t *d = dst;
    for (size_t i = 0; i < len; i++)
    {
        d[i] = (uint8_t)value;
    }
    return dst;
}

static void uart_char(char c)
{
    while (!(REG(0x4000441c) & (1U << 7)))
    {
    }
    REG(0x40004428) = (uint32_t)c;
}

static void uart_text(const char *s)
{
    while (*s)
    {
        uart_char(*s++);
    }
}

static void uart_number(uint32_t n)
{
    char digits[10];
    unsigned count = 0;
    do
    {
        digits[count++] = (char)('0' + n % 10U);
        n /= 10U;
    }
    while (n);
    while (count)
    {
        uart_char(digits[--count]);
    }
}

void board_init(void)
{
    /* usart2 tx on pa2, about 115200 baud */
    REG(0x4002104c) |= 1U;
    REG(0x40021058) |= 1U << 17;
    REG(0x48000000) = (REG(0x48000000) & ~(3U << 4)) | (2U << 4);
    REG(0x48000020) = (REG(0x48000020) & ~(15U << 8)) | (7U << 8);
    REG(0x4000440c) = 35U;
    REG(0x40004400) = (1U << 3) | 1U;

    /* enable and reset dwt cycle counter */
    REG(0xe000edfc) |= 1U << 24;
    REG(0xe0001000) |= 1U;
    REG(0xe0001004) = 0;
}

void board_print_header(void)
{
    uart_text("variant,operation,cycles\r\n");
}

void board_print_cycles(const char *operation, uint32_t cycles)
{
    uart_text(VARIANT);
    uart_char(',');
    uart_text(operation);
    uart_char(',');
    uart_number(cycles);
    uart_text("\r\n");
}

void board_error(const char *message)
{
    uart_text("ERROR: ");
    uart_text(message);
    uart_text("\r\n");
    while (1)
    {
    }
}

void board_finish(void)
{
    uart_text("END\r\n");
}

void Reset_Handler(void)
{
    uint32_t *src = &_sidata;
    for (uint32_t *dst = &_sdata; dst < &_edata; dst++)
    {
        *dst = *src++;
    }
    for (uint32_t *dst = &_sbss; dst < &_ebss; dst++)
    {
        *dst = 0;
    }
    main();
    while (1)
    {
    }
}

static void Default_Handler(void)
{
    while (1)
    {
    }
}

__attribute__((used, section(".isr_vector")))
const uintptr_t vectors[16] =
{
    (uintptr_t)&_estack, (uintptr_t)Reset_Handler,
    (uintptr_t)Default_Handler, (uintptr_t)Default_Handler,
    (uintptr_t)Default_Handler, (uintptr_t)Default_Handler,
    (uintptr_t)Default_Handler, 0, 0, 0, 0,
    (uintptr_t)Default_Handler, (uintptr_t)Default_Handler,
    0, (uintptr_t)Default_Handler, (uintptr_t)Default_Handler
};
