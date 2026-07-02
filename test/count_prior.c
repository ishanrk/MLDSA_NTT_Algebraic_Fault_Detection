#include "mldsa_checker.h"

#include <stdio.h>

static unsigned adds, subs, muls;

uint32_t count_add(uint32_t a, uint32_t b);
uint32_t count_sub(uint32_t a, uint32_t b);
uint32_t count_mul(uint32_t a, uint32_t b);

uint32_t mldsa_add(uint32_t a, uint32_t b)
{
    adds++;
    return count_add(a, b);
}

uint32_t mldsa_sub(uint32_t a, uint32_t b)
{
    subs++;
    return count_sub(a, b);
}

uint32_t mldsa_mul(uint32_t a, uint32_t b)
{
    muls++;
    return count_mul(a, b);
}

int main(void)
{
    mldsa_poly a = {{0}};
    mldsa_ntt r;
    mldsa_ntt_forward(&r, &a);
    unsigned x = muls, y = adds, z = subs;
    adds = subs = muls = 0;
    if (mldsa_ntt_forward_prior(&r, &a))
        return 1;
    printf("{\"baseline\":{\"mul\":%u,\"add\":%u,\"sub\":%u},"
           "\"prior\":{\"mul\":%u,\"add\":%u,\"sub\":%u},"
           "\"extra\":{\"mul\":%u,\"add\":%u,\"sub\":%u}}\n",
           x, y, z, muls, adds, subs, muls - x, adds - y, subs - z);
    return 0;
}
