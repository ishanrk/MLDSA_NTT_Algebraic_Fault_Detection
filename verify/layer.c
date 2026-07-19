#include "mldsa_poly.h"

#include <assert.h>

static const uint32_t zetas[MLDSA_N] = {
#include "../src/zetas.inc"
};

static mldsa_poly input;
static uint32_t products[128], sums[128], diffs[128];
static unsigned pair;
uint32_t nondet_u32(void);

enum { LEN = MLDSA_N >> (LAYER + 1), BASE = 1U << LAYER };

static unsigned low(void)
{
    assert(pair < 128);
    return 2U * LEN * (pair / LEN) + pair % LEN;
}

uint32_t mldsa_mul(uint32_t a, uint32_t b)
{
    unsigned j = low();
    assert(a == zetas[BASE + j / (2U * LEN)]);
    assert(b == input.c[j + LEN]);
    return products[pair];
}

uint32_t mldsa_add(uint32_t a, uint32_t b)
{
    unsigned j = low();
    assert(a == input.c[j] && b == products[pair]);
    return sums[pair];
}

uint32_t mldsa_sub(uint32_t a, uint32_t b)
{
    unsigned j = low();
    assert(a == input.c[j] && b == products[pair]);
    return diffs[pair++];
}

void layer(void)
{
    mldsa_ntt state, *r = &state;
    const mldsa_poly *a = &input;
    unsigned len = LEN, k = BASE - 1U;
    for (unsigned i = 0; i < MLDSA_N; i++) {
        input.c[i] = nondet_u32();
        __CPROVER_assume(input.c[i] < MLDSA_Q);
    }
#include "forward_copy.inc"
    for (unsigned i = 0; i < 128; i++) {
        products[i] = nondet_u32();
        sums[i] = nondet_u32();
        diffs[i] = nondet_u32();
        __CPROVER_assume(products[i] < MLDSA_Q);
        __CPROVER_assume(sums[i] < MLDSA_Q);
        __CPROVER_assume(diffs[i] < MLDSA_Q);
    }
#include "forward_layer.inc"
    assert(pair == 128 && k == 2U * BASE - 1U);
    for (unsigned i = 0; i < 128; i++) {
        unsigned j = 2U * LEN * (i / LEN) + i % LEN;
        assert(r->c[j] == sums[i]);
        assert(r->c[j + LEN] == diffs[i]);
    }
}
