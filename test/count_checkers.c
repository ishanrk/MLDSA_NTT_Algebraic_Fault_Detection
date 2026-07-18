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
    mldsa_poly a;
    mldsa_ntt r;
    for (unsigned i = 0; i < MLDSA_N; i++)
        a.c[i] = ((i + 1U) * (i + 17U)) % MLDSA_Q;
    mldsa_ntt_forward(&r, &a);
    printf("{\"baseline\":{\"mul\":%u,\"add\":%u,\"sub\":%u},", muls, adds, subs);
    adds = subs = muls = 0;
    if (mldsa_ntt_forward_prior(&r, &a))
        return 1;
    printf("\"prior\":{\"mul\":%u,\"add\":%u,\"sub\":%u},", muls, adds, subs);
    adds = subs = muls = 0;
    if (mldsa_ntt_forward_our(&r, &a))
        return 2;
    printf("\"our\":{\"mul\":%u,\"add\":%u,\"sub\":%u}}\n", muls, adds, subs);
    return 0;
}
