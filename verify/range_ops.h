#include "mldsa_poly.h"

#include <assert.h>

uint32_t nondet_u32(void);

static uint32_t residue(void)
{
    uint32_t r = nondet_u32();
    __CPROVER_assume(r < MLDSA_Q);
    return r;
}

uint32_t mldsa_add(uint32_t a, uint32_t b)
{
    assert(a < MLDSA_Q && b < MLDSA_Q);
    return residue();
}

uint32_t mldsa_sub(uint32_t a, uint32_t b)
{
    assert(a < MLDSA_Q && b < MLDSA_Q);
    return residue();
}

uint32_t mldsa_mul(uint32_t a, uint32_t b)
{
    assert(a < MLDSA_Q && b < MLDSA_Q);
    return residue();
}
