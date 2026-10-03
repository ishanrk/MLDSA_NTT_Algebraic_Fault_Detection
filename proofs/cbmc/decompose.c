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

    mldsa44_decompose(r, &hi, &lo);

    int64_t rebuilt = (int64_t)hi * MLDSA44_ALPHA + lo;
    assert(hi < 44U);
    assert(lo >= -MLDSA44_GAMMA2 && lo <= MLDSA44_GAMMA2);
    assert(lo != -MLDSA44_GAMMA2 || hi == 0U);
    assert(rebuilt == (int64_t)r || rebuilt == (int64_t)r - MLDSA_Q);
    assert(r != MLDSA_Q - 1U || (hi == 0U && lo == -1));
#ifdef CHECK_WRAPPERS
    assert(mldsa44_highbits(r) == hi);
    assert(mldsa44_lowbits(r) == lo);
#endif
}
