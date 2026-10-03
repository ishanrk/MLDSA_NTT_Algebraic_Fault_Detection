#include <stddef.h>
#include <stdint.h>


// linker symbols mark the stack and the data and bss sections
extern uint32_t _estack, _sidata, _sdata, _edata, _sbss, _ebss;
extern int main(void);

void *memcpy(void *dst, const void *src, size_t len)
{
    uint8_t *d = dst;
    const uint8_t *s = src;
    for (size_t i = 0; i < len; i++) d[i] = s[i];
    return dst;
}

void *memset(void *dst, int byte, size_t len)
{
    uint8_t *d = dst;
    for (size_t i = 0; i < len; i++) d[i] = (uint8_t)byte;
    return dst;
}

// archie stops here and saves the result from ram
__attribute__((noinline, used)) void emu_done(void)
{

    // keep this address visible so archie can stop here
    for (;;) __asm__ volatile ("wfi");
}

void Reset_Handler(void)
{
    // copy initialized data from flash to ram
    uint32_t *src = &_sidata;
    for (uint32_t *dst = &_sdata; dst < &_edata; dst++) *dst = *src++;
    for (uint32_t *dst = &_sbss; dst < &_ebss; dst++) *dst = 0;
    main();
    emu_done();
}

static void Default_Handler(void)
{
    for (;;) __asm__ volatile ("wfi"); // wait for an interrupt
}


// cortex m4 starts from this vector table
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
