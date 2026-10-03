#include "mldsa_poly.h"

#include <assert.h>
#include <stdint.h>

uint32_t nondet_u32(void);
uint64_t nondet_u64(void);
int32_t nondet_i32(void);

void add(void)
{
    uint32_t a = nondet_u32();
    uint32_t b = nondet_u32();
    __CPROVER_assume(a < MLDSA_Q && b < MLDSA_Q);
    uint32_t sum = a + b;
    uint32_t result = mldsa_add(a, b);
    assert(result < MLDSA_Q);
    assert(result == (sum >= MLDSA_Q ? sum - MLDSA_Q : sum));
}

void sub(void)
{
    uint32_t a = nondet_u32();
    uint32_t b = nondet_u32();
    __CPROVER_assume(a < MLDSA_Q && b < MLDSA_Q);
    uint32_t result = mldsa_sub(a, b);
    assert(result < MLDSA_Q);
    assert((uint64_t)result + b == a ||
           (uint64_t)result + b == (uint64_t)a + MLDSA_Q);
}

void center(void)
{
    uint32_t a = nondet_u32();
    __CPROVER_assume(a < MLDSA_Q);
    int32_t result = mldsa_center(a);
    assert(result >= -4190208 && result <= 4190208);
    assert((int64_t)result == a || (int64_t)result == (int64_t)a - MLDSA_Q);
    assert(mldsa_uncenter(result) == a);
}

void reduce(void)
{
    uint64_t a = nondet_u64();
    uint32_t result = mldsa_reduce(a);
    assert(result < MLDSA_Q);
    assert((uint64_t)result == a % (uint64_t)MLDSA_Q);
}
