#include "bench_plan.h"
#include "platform.h"
#include "target.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

extern int benchmark_entry(void);
static uint32_t clock_value = UINT32_MAX - 3U * 2U * BENCH_CALIBRATION_PAIRS - 500U;
static unsigned clock_calls, marker;

void platform_write(const char *text)
{
    fputs(text, stdout);
}

void physical_u32(uint32_t value)
{
    printf("%u", value);
}

int physical_dwt_init(void)
{
    return getenv("MLDSA_TEST_DWT_UNAVAILABLE") == NULL;
}

uint32_t physical_cycles(void)
{
    clock_calls++;
    clock_value += clock_calls <= 2U * BENCH_CALIBRATION_PAIRS ? 3U :
                   clock_calls % 2U ? 100U : 1000U;
    return clock_value;
}

uint32_t physical_stack_fill(void)
{
    return marker++;
}

uint32_t physical_stack_used(uint32_t start)
{
    return 4096U + start % 13U * 4U;
}

int main(void)
{
    platform_write("{\"event\":\"ready\",\"synthetic\":true,\"board\":\"" PHYSICAL_BOARD
                   "\",\"mcu\":\"" PHYSICAL_MCU "\",\"variant\":\"" PHYSICAL_VARIANT
                   "\",\"kind\":\"bench\",\"plan_sha256\":\"" BENCH_PLAN_SHA256 "\"}\n");
    int status = benchmark_entry();
    printf("{\"event\":\"done\",\"exit_code\":%d}\n", status);
    return status;
}
