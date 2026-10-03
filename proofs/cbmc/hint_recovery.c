#include "mldsa44_internal.h"

#include <assert.h>
#include <stdint.h>

uint32_t nondet_u32(void);
int32_t nondet_i32(void);

void harness(void)
{
    uint32_t r = nondet_u32();
    int32_t delta = nondet_i32();
    __CPROVER_assume(r < MLDSA_Q);
    __CPROVER_assume(delta >= -MLDSA44_GAMMA2 && delta <= MLDSA44_GAMMA2);

    uint32_t z = mldsa_uncenter(delta);
    uint32_t changed = mldsa_add(r, z);
    uint8_t hint = mldsa44_make_hint(z, r);
    uint32_t recovered = mldsa44_use_hint(hint, r);

    assert(hint <= 1U);
    assert(recovered == mldsa44_highbits(changed));
}
