#include "mldsa44_internal.h"

#include <assert.h>
#include <stdint.h>

uint32_t nondet_u32(void);
uint8_t nondet_u8(void);

void harness(void)
{
    uint32_t r = nondet_u32();
    uint8_t hint = nondet_u8();
    uint32_t hi;
    int32_t lo;
    __CPROVER_assume(r < MLDSA_Q);
    __CPROVER_assume(hint <= 1U);
    mldsa44_decompose(r, &hi, &lo);

    uint32_t result = mldsa44_use_hint(hint, r);
    assert(result < 44U);
    if (hint == 0U)
    {
        assert(result == hi);
    }
    else if (lo > 0)
    {
        assert(result == (hi == 43U ? 0U : hi + 1U));
    }
    else
    {
        assert(result == (hi == 0U ? 43U : hi - 1U));
    }
}
