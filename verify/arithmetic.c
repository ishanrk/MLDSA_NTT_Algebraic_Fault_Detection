#include "mldsa_poly.h"

#include <assert.h>

uint32_t nondet_u32(void);
uint64_t nondet_u64(void);
int32_t nondet_i32(void);

void reduce(void)
{
    uint64_t a = nondet_u64();
    uint32_t r = mldsa_reduce(a);
    assert(r < MLDSA_Q);
    assert((uint64_t)r == a % (uint64_t)MLDSA_Q);
}

void add(void)
{
    uint32_t a = nondet_u32(), b = nondet_u32();
    __CPROVER_assume(a < MLDSA_Q && b < MLDSA_Q);
    uint32_t r = mldsa_add(a, b);
    assert(r < MLDSA_Q);
    assert(r == ((uint64_t)a + b) % MLDSA_Q);
}

void sub(void)
{
    uint32_t a = nondet_u32(), b = nondet_u32();
    __CPROVER_assume(a < MLDSA_Q && b < MLDSA_Q);
    uint32_t r = mldsa_sub(a, b);
    assert(r < MLDSA_Q);
    assert(r == ((uint64_t)a + MLDSA_Q - b) % MLDSA_Q);
}

void mul(void)
{
    uint32_t a = nondet_u32(), b = nondet_u32();
    __CPROVER_assume(a < MLDSA_Q && b < MLDSA_Q);
    assert((uint64_t)a * b <= UINT64_C(70231372333056));
    uint32_t r = mldsa_mul(a, b);
    assert(r < MLDSA_Q);
    assert(r == (uint64_t)a * b % MLDSA_Q);
}

void center(void)
{
    uint32_t a = nondet_u32();
    __CPROVER_assume(a < MLDSA_Q);
    int32_t c = mldsa_center(a);
    assert(c >= -4190208 && c <= 4190208);
    assert(c == (a <= MLDSA_Q / 2U ? (int64_t)a : (int64_t)a - MLDSA_Q));
    assert(mldsa_uncenter(c) == a);
}

void uncenter(void)
{
    int32_t a = nondet_i32();
    __CPROVER_assume(a >= -4190208 && a <= 4190208);
    uint32_t r = mldsa_uncenter(a);
    assert(r < MLDSA_Q);
    assert((int64_t)r == (a < 0 ? (int64_t)a + MLDSA_Q : a));
    assert(mldsa_center(r) == a);
}
