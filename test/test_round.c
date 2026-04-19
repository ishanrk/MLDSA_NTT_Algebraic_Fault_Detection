#include "mldsa44_internal.h"

#include <stdio.h>
#include <stdlib.h>

static uint32_t state = 20444U;

static uint32_t rand32(void)
{
    state = state * 1664525U + 1013904223U;
    return state;
}

static void check(uint32_t r)
{
    uint32_t hi;
    int32_t lo;
    int64_t x;

    mldsa44_power2round(r, &hi, &lo);
    x = (int64_t)hi * (1 << MLDSA44_D) + lo;
    if (x != r || lo < -4095 || lo > 4096 || hi > 1023U)
        abort();

    mldsa44_decompose(r, &hi, &lo);
    x = (int64_t)hi * MLDSA44_ALPHA + lo;
    if ((x + MLDSA_Q) % MLDSA_Q != r || hi > 43U ||
        lo < -MLDSA44_GAMMA2 || lo > MLDSA44_GAMMA2)
        abort();
    if (mldsa44_highbits(r) != hi || mldsa44_lowbits(r) != lo)
        abort();
    if (mldsa44_use_hint(0, r) != hi)
        abort();

    for (int32_t z = -78; z <= 78; z += 13) {
        uint32_t v = mldsa_add(r, mldsa_uncenter(z));
        uint8_t h = mldsa44_make_hint(mldsa_uncenter(z), r);
        if (mldsa44_use_hint(h, r) != mldsa44_highbits(v))
            abort();
    }
}

int main(void)
{
    uint32_t edge[] = {0U, 1U, MLDSA_Q - 1U, MLDSA_Q - 2U,
                       4095U, 4096U, 4097U, 95231U, 95232U, 95233U,
                       MLDSA44_ALPHA - 1U, MLDSA44_ALPHA};
    for (unsigned i = 0; i < sizeof edge / sizeof edge[0]; i++)
        check(edge[i]);
    for (unsigned i = 0; i < 100000U; i++)
        check(rand32() % MLDSA_Q);
    puts("rounding invariants passed: 100000 random residues");
    return EXIT_SUCCESS;
}
