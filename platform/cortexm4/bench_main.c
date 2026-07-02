#include "core.h"
#include "mldsa44.h"
#include "mldsa_poly.h"
#include "mldsa_checker.h"
#include "platform.h"

#include <stdint.h>

static mldsa_poly a, b, out;
static mldsa_ntt an, bn, pn;
static uint8_t pk[MLDSA44_PUBLICKEY_BYTES], sk[MLDSA44_SECRETKEY_BYTES];
static uint8_t sig[MLDSA44_SIGNATURE_BYTES];
static uint32_t samples[6][101];
static uint32_t stack[4];
static const unsigned lengths[6] = {101, 101, 101, 31, 31, 101};
static const char *const names[6] = {
    "ntt_forward", "ntt_inverse", "pointwise", "keygen", "sign", "verify"
};

static void put_u32(uint32_t n)
{
    char buf[12];
    unsigned i = sizeof buf - 1U;
    buf[i] = 0;
    do {
        buf[--i] = (char)('0' + n % 10U);
        n /= 10U;
    } while (n != 0U);
    platform_write(buf + i);
}

static void emit(void)
{
    for (unsigned op = 0; op < 6; op++) {
        for (unsigned i = 0; i < lengths[op]; i++) {
            platform_write("{\"op\":\"");
            platform_write(names[op]);
            platform_write("\",\"sample\":");
            put_u32(i);
            platform_write(",\"cycles\":");
            put_u32(samples[op][i]);
            platform_write("}\n");
        }
    }
    for (unsigned i = 0; i < 4; i++) {
        unsigned op = i == 0U ? 0U : i + 2U;
        platform_write("{\"op\":\"");
        platform_write(names[op]);
        platform_write("\",\"stack_bytes\":");
        put_u32(stack[i]);
        platform_write("}\n");
    }
}

static uint32_t elapsed(uint32_t start, uint32_t end, uint32_t overhead)
{
    uint32_t n = end - start;
    return n > overhead ? n - overhead : 0U;
}

static int forward(mldsa_ntt *r, const mldsa_poly *x)
{
#ifdef MLDSA_PRIOR_CHECKER
    return mldsa_ntt_forward_prior(r, x);
#else
    mldsa_ntt_forward(r, x);
    return 0;
#endif
}

int main(void)
{
    const uint8_t msg[] = "Cortex M4 portable baseline";
    const uint8_t ctx[] = "arm";
    uint8_t seed[32] = {0}, rnd[32] = {0};
    uint32_t overhead = UINT32_MAX;

    if (!platform_dwt_init()) {
        platform_write("DWT UNAVAILABLE\n");
        return 1;
    }
    for (unsigned i = 0; i < 101; i++) {
        uint32_t t = platform_cycles();
        uint32_t n = platform_cycles() - t;
        if (n < overhead)
            overhead = n;
    }
    for (unsigned i = 0; i < MLDSA_N; i++) {
        a.c[i] = ((i + 1U) * (i + 17U)) % MLDSA_Q;
        b.c[i] = ((3U * i + 2U) * (7U * i + 5U)) % MLDSA_Q;
    }
    if (forward(&an, &a) || forward(&bn, &b))
        return 2;

    for (unsigned i = 0; i < lengths[0]; i++) {
        uint32_t t = platform_cycles();
        int rc = forward(&pn, &a);
        uint32_t u = platform_cycles();
        samples[0][i] = elapsed(t, u, overhead);
        if (rc)
            return 2;
    }
    for (unsigned i = 0; i < lengths[1]; i++) {
        uint32_t t = platform_cycles();
        mldsa_ntt_inverse(&out, &an);
        uint32_t u = platform_cycles();
        samples[1][i] = elapsed(t, u, overhead);
    }
    for (unsigned i = 0; i < lengths[2]; i++) {
        uint32_t t = platform_cycles();
        mldsa_ntt_mul(&pn, &an, &bn);
        uint32_t u = platform_cycles();
        samples[2][i] = elapsed(t, u, overhead);
    }
    for (unsigned i = 0; i < lengths[3]; i++) {
        seed[0] = (uint8_t)i;
        uint32_t t = platform_cycles();
        int rc = mldsa44_keygen(pk, sk, seed);
        uint32_t u = platform_cycles();
        samples[3][i] = elapsed(t, u, overhead);
        if (rc)
            return 2;
    }
    for (unsigned i = 0; i < lengths[4]; i++) {
        rnd[0] = (uint8_t)i;
        uint32_t t = platform_cycles();
        int rc = mldsa44_sign(sig, sk, sizeof sk, msg, sizeof msg - 1U,
                              ctx, sizeof ctx - 1U, rnd);
        uint32_t u = platform_cycles();
        samples[4][i] = elapsed(t, u, overhead);
        if (rc)
            return 2;
    }
    for (unsigned i = 0; i < lengths[5]; i++) {
        uint32_t t = platform_cycles();
        int rc = mldsa44_verify(pk, sizeof pk, msg, sizeof msg - 1U,
                                ctx, sizeof ctx - 1U, sig, sizeof sig);
        uint32_t u = platform_cycles();
        samples[5][i] = elapsed(t, u, overhead);
        if (rc)
            return 3;
    }
    uint32_t mark = platform_stack_fill();
    int rc = forward(&pn, &a);
    stack[0] = platform_stack_used(mark);
    if (rc)
        return 2;
    mark = platform_stack_fill();
    rc = mldsa44_keygen(pk, sk, seed);
    stack[1] = platform_stack_used(mark);
    if (rc)
        return 2;
    mark = platform_stack_fill();
    rc = mldsa44_sign(sig, sk, sizeof sk, msg, sizeof msg - 1U,
                          ctx, sizeof ctx - 1U, rnd);
    stack[2] = platform_stack_used(mark);
    if (rc)
        return 4;
    mark = platform_stack_fill();
    rc = mldsa44_verify(pk, sizeof pk, msg, sizeof msg - 1U,
                        ctx, sizeof ctx - 1U, sig, sizeof sig);
    stack[3] = platform_stack_used(mark);
    if (rc)
        return 5;
    platform_write("{\"op\":\"overhead\",\"sample\":0,\"cycles\":");
    put_u32(overhead);
    platform_write("}\n");
    emit();
    return 0;
}
