#include "mldsa44_internal.h"

void mldsa44_power2round(uint32_t r, uint32_t *hi, int32_t *lo)
{
    int32_t x = (int32_t)r;
    int32_t t = x % (1 << MLDSA44_D);
    if (t > (1 << (MLDSA44_D - 1)))
        t -= 1 << MLDSA44_D;
    *hi = (uint32_t)((x - t) / (1 << MLDSA44_D));
    *lo = t;
}

void mldsa44_decompose(uint32_t r, uint32_t *hi, int32_t *lo)
{
    int32_t x = (int32_t)r;
    int32_t t = x % MLDSA44_ALPHA;
    if (t > MLDSA44_GAMMA2)
        t -= MLDSA44_ALPHA;
    if (x - t == MLDSA_Q - 1) {
        *hi = 0;
        *lo = t - 1;
    } else {
        *hi = (uint32_t)((x - t) / MLDSA44_ALPHA);
        *lo = t;
    }
}

uint32_t mldsa44_highbits(uint32_t r)
{
    uint32_t hi;
    int32_t lo;
    mldsa44_decompose(r, &hi, &lo);
    return hi;
}

int32_t mldsa44_lowbits(uint32_t r)
{
    uint32_t hi;
    int32_t lo;
    mldsa44_decompose(r, &hi, &lo);
    return lo;
}

uint8_t mldsa44_make_hint(uint32_t z, uint32_t r)
{
    return (uint8_t)(mldsa44_highbits(r) != mldsa44_highbits(mldsa_add(r, z)));
}

uint32_t mldsa44_use_hint(uint8_t h, uint32_t r)
{
    uint32_t hi;
    int32_t lo;
    mldsa44_decompose(r, &hi, &lo);
    if (h == 0U)
        return hi;
    return lo > 0 ? (hi + 1U) % 44U : (hi + 43U) % 44U;
}

int mldsa44_norm(const mldsa_poly *a, uint32_t bound)
{
    for (unsigned i = 0; i < MLDSA_N; i++) {
        int32_t x = mldsa_center(a->c[i]);
        if (x < 0)
            x = -x;
        if ((uint32_t)x >= bound)
            return 1;
    }
    return 0;
}
