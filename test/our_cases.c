#include "mldsa_checker.h"
#include "platform.h"
#include "our_cases.h"

static unsigned count, target, n, loc[2];
static uint32_t delta[2], weights[MLDSA_N];

void test_our_inject(unsigned call, unsigned r, uint32_t d)
{
    count = 0;
    target = call;
    n = 1;
    loc[0] = r;
    delta[0] = d;
}

void mldsa_ntt_test_fault(unsigned l, uint32_t c[MLDSA_N])
{
    if (l == 0U)
        count++;
    if (count != target)
        return;
    for (unsigned i = 0; i < n; i++) {
        if (loc[i] / MLDSA_N == l)
            c[loc[i] % MLDSA_N] = mldsa_add(c[loc[i] % MLDSA_N], delta[i]);
    }
}

static uint32_t power(uint32_t x, unsigned k)
{
    uint32_t r = 1;
    for (; k; k /= 2U) {
        if (k % 2U)
            r = mldsa_mul(r, x);
        x = mldsa_mul(x, x);
    }
    return r;
}

static unsigned rev(unsigned x, unsigned bits)
{
    unsigned r = 0;
    for (unsigned i = 0; i < bits; i++) {
        r = 2U * r + x % 2U;
        x /= 2U;
    }
    return r;
}

static uint32_t response(unsigned r)
{
    unsigned l = r / MLDSA_N, i = r % MLDSA_N;
    unsigned len = MLDSA_N >> l;
    unsigned mu = rev(i / len, l), pos = i % len;
    uint32_t s = 0;
    for (unsigned j = mu; j < MLDSA_N; j += 1U << l)
        s = mldsa_add(s, mldsa_mul(weights[j], power(1753U, (2U * j + 1U) * pos)));
    return s;
}

static int same(const uint32_t *a, const uint32_t *b)
{
    for (unsigned i = 0; i < MLDSA_N; i++) {
        if (a[i] != b[i])
            return 0;
    }
    return 1;
}

int test_our(void)
{
    mldsa_poly a = {{0}}, back;
    mldsa_ntt baseline, got;
    uint32_t x = 20446U;
    const unsigned singles[] = {0, 127, 255, 256, 383, 511, 1024, 1151, 1279,
                                 1792, 1919, 2047, 2048, 2175, 2303};
    const unsigned pairs[][2] = {{1024, 1025}, {1024, 1279}, {256, 512},
                                  {511, 1792}, {1151, 2047}, {0, 2303},
                                  {127, 128}, {257, 513}, {775, 1480}, {2048, 2303}};
    const uint32_t mags[] = {1, 17, MLDSA_Q - 1U};

    target = 0;
    for (unsigned pos = 0; pos < 10; pos++) {
        for (unsigned i = 0; i < MLDSA_N; i++) {
            if (pos == 0U)
                a.c[i] = 0;
            else if (pos <= 3U) {
                unsigned j = pos == 1U ? 0U : pos == 2U ? 127U : 255U;
                a.c[i] = i == j ? 1U : 0U;
            } else if (pos == 4U)
                a.c[i] = MLDSA_Q - 1U;
            else if (pos == 5U)
                a.c[i] = i % 2U ? MLDSA_Q - 1U : 0U;
            else {
                x = x * 1664525U + 1013904223U;
                a.c[i] = x % MLDSA_Q;
            }
        }
        mldsa_ntt_forward(&baseline, &a);
        if (mldsa_ntt_forward_our(&got, &a) || !same(got.c, baseline.c))
            return 1;
        mldsa_ntt_inverse(&back, &got);
        if (!same(back.c, a.c))
            return 2;
    }
    platform_write("OUR NTT 10 cases PASS\n");
    for (unsigned i = 0; i < MLDSA_N; i++) {
        uint32_t z = power(1753U, 2U * i + 1U);
        uint32_t t = mldsa_sub(1U, power(z, MLDSA_Q - 2U));
        weights[i] = mldsa_mul(mldsa_mul(2U, power(MLDSA_N, MLDSA_Q - 2U)),
                              power(t, MLDSA_Q - 2U));
    }
    for (unsigned i = 0; i < sizeof singles / sizeof singles[0]; i++) {
        for (unsigned j = 0; j < sizeof mags / sizeof mags[0]; j++) {
            test_our_inject(1, singles[i], mags[j]);
            if (mldsa_ntt_forward_our(&got, &a) != -1 || same(got.c, baseline.c))
                return 3;
        }
    }
    platform_write("OUR single faults 45 cases PASS\n");
    uint32_t sum = 0;
    for (unsigned i = 0; i < MLDSA_N; i++)
        sum = mldsa_add(sum, a.c[i]);
    for (unsigned i = 0; i < sizeof pairs / sizeof pairs[0]; i++) {
        for (unsigned j = 0; j < sizeof mags / sizeof mags[0]; j++) {
            test_our_inject(1, pairs[i][0], mags[j]);
            n = 2;
            loc[1] = pairs[i][1];
            uint32_t t = mldsa_mul(response(loc[0]), delta[0]);
            delta[1] = mldsa_sub(0U, mldsa_mul(t, power(response(loc[1]), MLDSA_Q - 2U)));
            if (delta[1] == 0U || mldsa_ntt_forward_our(&got, &a) != -1 ||
                same(got.c, baseline.c))
                return 4;
            uint32_t check = 0;
            for (unsigned k = 0; k < MLDSA_N; k++)
                check = mldsa_add(check, mldsa_mul(weights[rev(k, 8)], got.c[k]));
            if (check != sum)
                return 5;
        }
    }
    target = 0;
    platform_write("OUR cancelling fault pairs 30 cases PASS\n");
    return 0;
}
