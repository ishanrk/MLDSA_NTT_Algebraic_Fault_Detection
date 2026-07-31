#include "mldsa_checker.h"

#include <assert.h>

#define mldsa_mul unused_mul
#include "../src/poly.c"
#undef mldsa_mul

#ifdef PRIOR
#include "../src/prior_tables.inc"
#else
#include "../src/our_tables.inc"
#endif

uint32_t nondet_u32(void);
static uint32_t term[2], weight[2], coeff;
static unsigned calls;

void base(void)
{
#ifdef PRIOR
#include "prior_initial.inc"
#else
#include "our_initial.inc"
#endif
    assert(x == 0 && y == 0 && u == 0 && v == 0);
}

uint32_t mldsa_mul(uint32_t a, uint32_t b)
{
    assert(calls < 2);
    assert(a == weight[calls] && b == coeff);
    assert(a < MLDSA_Q && b < MLDSA_Q);
    return term[calls++];
}

void input_step(void)
{
    mldsa_poly input, *a = &input;
    unsigned i = nondet_u32();
    uint32_t x = nondet_u32(), y = nondet_u32();
    __CPROVER_assume(i < MLDSA_N);
    __CPROVER_assume(x < MLDSA_Q && y < MLDSA_Q);
    uint32_t before_x = x, before_y = y;
    coeff = nondet_u32();
    term[0] = nondet_u32();
    __CPROVER_assume(coeff < MLDSA_Q && term[0] < MLDSA_Q);
    a->c[i] = coeff;
#ifdef PRIOR
    weight[0] = prior_beta[i];
#include "prior_input.inc"
#else
    weight[0] = our_beta[i];
#include "our_input.inc"
#endif
    assert(calls == 1);
    assert(x == ((uint64_t)before_x + coeff) % MLDSA_Q);
    assert(y == ((uint64_t)before_y + term[0]) % MLDSA_Q);
    assert(x < MLDSA_Q && y < MLDSA_Q);
    assert(a->c[i] == coeff);
}

void output_step(void)
{
    mldsa_ntt output, *r = &output;
    unsigned i = nondet_u32();
    uint32_t u = nondet_u32(), v = nondet_u32();
    __CPROVER_assume(i < MLDSA_N);
    __CPROVER_assume(u < MLDSA_Q && v < MLDSA_Q);
    uint32_t before_u = u, before_v = v;
    coeff = nondet_u32();
    term[0] = nondet_u32();
    term[1] = nondet_u32();
    __CPROVER_assume(coeff < MLDSA_Q && term[0] < MLDSA_Q && term[1] < MLDSA_Q);
    r->c[i] = coeff;
#ifdef PRIOR
    weight[0] = prior_a[i];
    if (i % 2U == 0U)
        weight[1] = prior_alpha[i / 2U];
#include "prior_output.inc"
    uint32_t second = i % 2U ? coeff : term[1];
    assert(calls == (i % 2U ? 1U : 2U));
#else
    weight[0] = our_a[i];
    weight[1] = our_alpha[i];
#include "our_output.inc"
    uint32_t second = term[1];
    assert(calls == 2);
#endif
    assert(u == ((uint64_t)before_u + term[0]) % MLDSA_Q);
    assert(v == ((uint64_t)before_v + second) % MLDSA_Q);
    assert(u < MLDSA_Q && v < MLDSA_Q);
    assert(r->c[i] == coeff);
}

static int decision(uint32_t x, uint32_t y, uint32_t u, uint32_t v)
{
#ifdef PRIOR
#include "prior_return.inc"
#else
#include "our_return.inc"
#endif
}

void decide(void)
{
    uint32_t x = nondet_u32(), y = nondet_u32();
    uint32_t u = nondet_u32(), v = nondet_u32();
    int rc = decision(x, y, u, v);
    assert(rc == (x == u && y == v ? 0 : -1));
    assert(decision(x, y, x, y) == 0);
}
