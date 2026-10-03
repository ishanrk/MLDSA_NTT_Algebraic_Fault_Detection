#include "mldsa44_internal.h"

#include <assert.h>
#include <stdint.h>

uint32_t nondet_u32(void);

void harness(void)
{
    uint32_t r = nondet_u32();
    uint32_t hi;
    int32_t lo;
    __CPROVER_assume(r < MLDSA_Q);

    mldsa44_power2round(r, &hi, &lo);

    assert(hi <= 1023U);
    assert(lo > -4096 && lo <= 4096);
    assert((int64_t)r == (int64_t)hi * 8192 + lo);
}
