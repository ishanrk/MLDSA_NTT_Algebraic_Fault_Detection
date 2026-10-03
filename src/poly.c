#include "mldsa_poly.h"

uint32_t mldsa_reduce(uint64_t a)
{
    for (unsigned i = 0; i < 6; i++)
    {
        a = (a & 0x7fffffU) + (a >> 23) * 8191U;
    }
    uint32_t r = (uint32_t)a - MLDSA_Q;
    return r + (MLDSA_Q & (0U - (r >> 31)));
}

uint32_t mldsa_add(uint32_t a, uint32_t b)
{
    uint32_t r = a + b - MLDSA_Q;
    return r + (MLDSA_Q & (0U - (r >> 31)));
}

uint32_t mldsa_sub(uint32_t a, uint32_t b)
{
    uint32_t r = a - b;
    return r + (MLDSA_Q & (0U - (r >> 31)));
}

uint32_t mldsa_mul(uint32_t a, uint32_t b)
{
    return mldsa_reduce((uint64_t)a * b);
}

int32_t mldsa_center(uint32_t a)
{
    uint32_t above = (MLDSA_Q / 2U - a) >> 31;
    return (int32_t)a - (int32_t)(above * MLDSA_Q);
}

uint32_t mldsa_uncenter(int32_t a)
{
    uint32_t negative = (uint32_t)a >> 31;
    return (uint32_t)(a + (int32_t)(negative * MLDSA_Q));
}

void mldsa_poly_add(mldsa_poly *r, const mldsa_poly *a, const mldsa_poly *b)
{
    for (unsigned i = 0; i < MLDSA_N; i++)
    {
        r->c[i] = mldsa_add(a->c[i], b->c[i]);
    }
}

void mldsa_poly_sub(mldsa_poly *r, const mldsa_poly *a, const mldsa_poly *b)
{
    for (unsigned i = 0; i < MLDSA_N; i++)
    {
        r->c[i] = mldsa_sub(a->c[i], b->c[i]);
    }
}

void mldsa_poly_mul(mldsa_poly *r, const mldsa_poly *a, const mldsa_poly *b)
{
    mldsa_ntt x, y, z;

    mldsa_ntt_forward(&x, a);
    mldsa_ntt_forward(&y, b);
    mldsa_ntt_mul(&z, &x, &y);
    mldsa_ntt_inverse(r, &z);
}
