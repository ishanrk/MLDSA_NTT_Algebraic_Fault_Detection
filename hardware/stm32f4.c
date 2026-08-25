#include "platform.h"
#include "target.h"
#include "bench_plan.h"

#include <stdint.h>

#define REG(address) (*(volatile uint32_t *)(address))
#define RCC 0x40023800U
#define GPIOA 0x40020000U
#define USART2 0x40004400U

void physical_u32(uint32_t value)
{
    char buf[12];
    unsigned i = sizeof buf - 1U;
    buf[i] = 0;
    do {
        buf[--i] = (char)('0' + value % 10U);
        value /= 10U;
    } while (value != 0U);
    platform_write(buf + i);
}

void platform_write(const char *text)
{
    while (*text) {
        while ((REG(USART2) & (1U << 7)) == 0U) {
        }
        REG(USART2 + 4U) = (uint8_t)*text++;
    }
}

static void field(const char *name, uint32_t value)
{
    platform_write(",\"");
    platform_write(name);
    platform_write("\":");
    physical_u32(value);
}

void physical_init(void)
{
    REG(0xe000e010U) = 0;
    REG(0xe000ed88U) &= ~(15U << 20);
    REG(RCC) |= 1U;
    while ((REG(RCC) & 2U) == 0U) {
    }
    REG(RCC + 8U) = 0;
    while ((REG(RCC + 8U) & 12U) != 0U) {
    }
    REG(RCC) &= ~((1U << 24) | (1U << 16));
    while ((REG(RCC) & (1U << 25)) != 0U) {
    }
    REG(0x40023c00U) = 0;
    REG(RCC + 0x30U) |= 1U;
    REG(RCC + 0x40U) |= 1U << 17;
    (void)REG(RCC + 0x40U);
    REG(GPIOA) = (REG(GPIOA) & ~(15U << 4)) | (10U << 4);
    REG(GPIOA + 8U) = (REG(GPIOA + 8U) & ~(15U << 4)) | (5U << 4);
    REG(GPIOA + 12U) = (REG(GPIOA + 12U) & ~(15U << 4)) | (1U << 6);
    REG(GPIOA + 0x20U) = (REG(GPIOA + 0x20U) & ~(255U << 8)) | (0x77U << 8);
    REG(USART2 + 0x0cU) = 0;
    REG(USART2 + 0x10U) = 0;
    REG(USART2 + 0x14U) = 0;
    REG(USART2 + 8U) = 139U;
    REG(USART2 + 0x0cU) = (1U << 13) | (1U << 3) | (1U << 2);
    platform_write("{\"event\":\"ready\",\"board\":\"" PHYSICAL_BOARD
                   "\",\"mcu\":\"" PHYSICAL_MCU "\",\"variant\":\"" PHYSICAL_VARIANT
                   "\",\"kind\":\"" PHYSICAL_KIND "\",\"plan_sha256\":\"" BENCH_PLAN_SHA256 "\"");
    field("cpuid", REG(0xe000ed00U));
    field("dbg_idcode", REG(0xe0042000U));
    field("uid0", REG(0x1fff7a10U));
    field("uid1", REG(0x1fff7a14U));
    field("uid2", REG(0x1fff7a18U));
    field("flash_kib", *(volatile const uint16_t *)0x1fff7a22U);
    field("nominal_cpu_hz", 16000000U);
    field("rcc_cr", REG(RCC));
    field("rcc_cfgr", REG(RCC + 8U));
    field("flash_acr", REG(0x40023c00U));
    field("cpacr", REG(0xe000ed88U));
    uint32_t primask;
    __asm volatile("mrs %0, primask" : "=r"(primask));
    field("primask", primask);
    platform_write("}\n");
    while (1) {
        while ((REG(USART2) & (1U << 5)) == 0U) {
        }
        if ((uint8_t)REG(USART2 + 4U) == (uint8_t)'R')
            break;
    }
}

void platform_done(int status)
{
    platform_write("{\"event\":\"done\",\"exit_code\":");
    physical_u32((uint32_t)status);
    platform_write("}\n");
    while ((REG(USART2) & (1U << 6)) == 0U) {
    }
    for (;;) {
    }
}
