#include "mldsa_poly.h"

#include <assert.h>

#define mldsa_mul unused_mul
#include "../src/poly.c"
#undef mldsa_mul

uint32_t nondet_u32(void);
static uint32_t term, want_z, want_b;

uint32_t mldsa_mul(uint32_t a, uint32_t b)
{
    assert(a == want_z && b == want_b);
    assert(a < MLDSA_Q && b < MLDSA_Q);
    return term;
}

void butterfly(void)
{
    mldsa_ntt state, *r = &state;
    uint32_t a = nondet_u32(), b = nondet_u32(), z = nondet_u32();
    unsigned l = nondet_u32(), pos = nondet_u32(), g = nondet_u32();
    __CPROVER_assume(a < MLDSA_Q && b < MLDSA_Q && z < MLDSA_Q);
    __CPROVER_assume(l < 8);
    unsigned len = 1U << l;
    __CPROVER_assume(pos < len && g < MLDSA_N / (2U * len));
    unsigned j = 2U * len * g + pos;
    r->c[j] = a;
    r->c[j + len] = b;
    term = nondet_u32();
    __CPROVER_assume(term < MLDSA_Q);
    want_z = z;
#ifdef INVERSE
    want_b = (uint32_t)(((uint64_t)a + MLDSA_Q - b) % MLDSA_Q);
#include "inverse_body.inc"
    assert(r->c[j] == ((uint64_t)a + b) % MLDSA_Q);
    assert(r->c[j + len] == term);
#else
    want_b = b;
#include "forward_body.inc"
    assert(r->c[j] == ((uint64_t)a + term) % MLDSA_Q);
    assert(r->c[j + len] == ((uint64_t)a + MLDSA_Q - term) % MLDSA_Q);
#endif
    assert(r->c[j] < MLDSA_Q && r->c[j + len] < MLDSA_Q);
}
