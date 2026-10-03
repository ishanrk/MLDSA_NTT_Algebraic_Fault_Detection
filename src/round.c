#include "mldsa44_internal.h"

void mldsa44_power2round(uint32_t r, uint32_t *hi, int32_t *lo)
{
    uint32_t t = r & ((1U << MLDSA44_D) - 1U);
    uint32_t upper = (4096U - t) >> 31;
    int32_t low = (int32_t)t - (int32_t)(upper << MLDSA44_D);
    *hi = (uint32_t)(((int32_t)r - low) >> MLDSA44_D);
    *lo = low;
}

void mldsa44_decompose(uint32_t r, uint32_t *hi, int32_t *lo)
{
    uint32_t q = r / MLDSA44_ALPHA;
    uint32_t rem = r - q * MLDSA44_ALPHA;
    uint32_t carry = (MLDSA44_GAMMA2 - rem) >> 31;
    int32_t low = (int32_t)rem - (int32_t)(carry * MLDSA44_ALPHA);
    uint32_t high = q + carry;
    uint32_t wrap = (r - (uint32_t)low == MLDSA_Q - 1U);
    *hi = high * (1U - wrap);
    *lo = low - (int32_t)wrap;
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
    {
        return hi;
    }
    return lo > 0 ? (hi + 1U) % 44U : (hi + 43U) % 44U;
}

int mldsa44_norm(const mldsa_poly *a, uint32_t bound)
{
    uint32_t bad = 0;
    for (unsigned i = 0; i < MLDSA_N; i++)
    {
        int32_t x = mldsa_center(a->c[i]);
        uint32_t mask = 0U - ((uint32_t)x >> 31);
        uint32_t magnitude = ((uint32_t)x ^ mask) - mask;
        bad |= (magnitude >= bound);
    }
    return (int)bad;
}
