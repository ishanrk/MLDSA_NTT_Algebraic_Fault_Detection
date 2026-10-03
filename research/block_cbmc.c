#include "mldsa_poly.h"
#include <assert.h>
#include <stdint.h>

uint32_t nondet_u32(void);
uint64_t nondet_u64(void);

void normalize(void)
{
    uint32_t sum = nondet_u32();
    uint32_t first = nondet_u32();
    __CPROVER_assume(sum < MLDSA_Q && first < MLDSA_Q);
    uint32_t correction = mldsa_sub(1, sum);
    uint32_t changed = mldsa_add(first, correction);
    assert(correction < MLDSA_Q && changed < MLDSA_Q);
    assert(mldsa_add(sum, correction) == 1);
    assert(mldsa_sub(changed, correction) == first);
}

void accumulator(void)
{
    uint64_t acc = nondet_u64();
    uint32_t weight = nondet_u32();
    uint32_t value = nondet_u32();
    const uint64_t term_bound = (uint64_t)(MLDSA_Q - 1U) * UINT32_MAX;
    __CPROVER_assume(weight < MLDSA_Q && acc <= 31U * term_bound);
    uint64_t term = (uint64_t)weight * value;
    uint64_t next = acc + term;
    assert(term <= term_bound);
    assert(next >= acc);
    assert(next <= 32U * term_bound);
}
