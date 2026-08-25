#include "bench_plan.h"
#include "mldsa44.h"
#include "mldsa_checker.h"
#include "mldsa_poly.h"
#include "mldsa_shake.h"
#include "platform.h"
#include "target.h"

#include <stdint.h>

static mldsa_poly a, b, out;
static mldsa_ntt an, bn, pn;
static uint8_t pk[MLDSA44_PUBLICKEY_BYTES], sk[MLDSA44_SECRETKEY_BYTES];
static uint8_t sig[MLDSA44_SIGNATURE_BYTES];
static uint32_t raw[6][BENCH_SAMPLES], stacks[4][BENCH_SAMPLES];
static uint32_t overhead[BENCH_CALIBRATION_PAIRS];
static mldsa_shake transcript;
static const char *const names[6] = {
    "ntt_forward", "ntt_inverse", "pointwise", "keygen", "sign", "verify"
};

static int forward(mldsa_ntt *r, const mldsa_poly *p)
{
#ifdef MLDSA_PRIOR_CHECKER
    return mldsa_ntt_forward_prior(r, p);
#elif defined(MLDSA_OUR_CHECKER)
    return mldsa_ntt_forward_our(r, p);
#else
    mldsa_ntt_forward(r, p);
    return 0;
#endif
}

static void emit(uint32_t correction)
{
    for (unsigned i = 0; i < BENCH_CALIBRATION_PAIRS; i++) {
        platform_write("{\"op\":\"overhead\",\"sample\":");
        physical_u32(i);
        platform_write(",\"cycles\":");
        physical_u32(overhead[i]);
        platform_write("}\n");
    }
    for (unsigned op = 0; op < 6; op++) {
        for (unsigned i = 0; i < BENCH_SAMPLES; i++) {
            platform_write("{\"op\":\"");
            platform_write(names[op]);
            platform_write("\",\"sample\":");
            physical_u32(i);
            platform_write(",\"raw_cycles\":");
            physical_u32(raw[op][i]);
            platform_write(",\"cycles\":");
            physical_u32(raw[op][i] > correction ? raw[op][i] - correction : 0U);
            platform_write("}\n");
        }
    }
    for (unsigned op = 0; op < 4; op++) {
        unsigned index = op == 0U ? 0U : op + 2U;
        for (unsigned i = 0; i < BENCH_SAMPLES; i++) {
            platform_write("{\"op\":\"");
            platform_write(names[index]);
            platform_write("\",\"sample\":");
            physical_u32(i);
            platform_write(",\"stack_bytes\":");
            physical_u32(stacks[op][i]);
            platform_write("}\n");
        }
    }
    uint8_t digest[32];
    mldsa_shake_squeeze(&transcript, digest, sizeof digest);
    platform_write("{\"event\":\"transcript\",\"shake256\":\"");
    for (unsigned i = 0; i < sizeof digest; i++) {
        const char hex[] = "0123456789abcdef";
        char text[3] = {hex[digest[i] >> 4], hex[digest[i] & 15U], 0};
        platform_write(text);
    }
    platform_write("\"}\n");
}

int main(void)
{
    const uint8_t msg[] = BENCH_MESSAGE, ctx[] = BENCH_CONTEXT;
    uint8_t seed[32], rnd[32] = {0};
    uint32_t correction = UINT32_MAX;
    if (!physical_dwt_init()) {
        platform_write("DWT UNAVAILABLE\n");
        return 1;
    }
    mldsa_shake_init(&transcript, 256);
    for (unsigned i = 0; i < BENCH_CALIBRATION_PAIRS; i++) {
        uint32_t t = physical_cycles();
        overhead[i] = physical_cycles() - t;
        if (overhead[i] < correction)
            correction = overhead[i];
    }
    for (unsigned i = 0; i < MLDSA_N; i++) {
        a.c[i] = ((i + 1U) * (i + 17U)) % MLDSA_Q;
        b.c[i] = ((3U * i + 2U) * (7U * i + 5U)) % MLDSA_Q;
    }
    if (forward(&an, &a) || forward(&bn, &b))
        return 2;
    for (unsigned i = 0; i < BENCH_SAMPLES; i++) {
        uint32_t mark = physical_stack_fill();
        uint32_t t = physical_cycles();
        int rc = forward(&pn, &a);
        uint32_t end = physical_cycles();
        raw[0][i] = end - t;
        stacks[0][i] = physical_stack_used(mark);
        if (rc)
            return 2;
    }
    for (unsigned i = 0; i < BENCH_SAMPLES; i++) {
        uint32_t t = physical_cycles();
        mldsa_ntt_inverse(&out, &an);
        uint32_t end = physical_cycles();
        raw[1][i] = end - t;
    }
    for (unsigned i = 0; i < BENCH_SAMPLES; i++) {
        uint32_t t = physical_cycles();
        mldsa_ntt_mul(&pn, &an, &bn);
        uint32_t end = physical_cycles();
        raw[2][i] = end - t;
    }
    for (unsigned i = 0; i < 32; i++)
        seed[i] = (uint8_t)i;
    for (unsigned i = 0; i < BENCH_SAMPLES; i++) {
        seed[0] = (uint8_t)i;
        uint32_t mark = physical_stack_fill();
        uint32_t t = physical_cycles();
        int rc = mldsa44_keygen(pk, sk, seed);
        uint32_t end = physical_cycles();
        raw[3][i] = end - t;
        stacks[1][i] = physical_stack_used(mark);
        if (rc)
            return 3;
        mldsa_shake_absorb(&transcript, pk, sizeof pk);
    }
    seed[0] = 0;
    if (mldsa44_keygen(pk, sk, seed))
        return 3;
    for (unsigned i = 0; i < BENCH_SAMPLES; i++) {
        rnd[0] = (uint8_t)i;
        uint32_t mark = physical_stack_fill();
        uint32_t t = physical_cycles();
        int rc = mldsa44_sign(sig, sk, sizeof sk, msg, sizeof msg - 1U,
                              ctx, sizeof ctx - 1U, rnd);
        uint32_t end = physical_cycles();
        raw[4][i] = end - t;
        stacks[2][i] = physical_stack_used(mark);
        if (rc || mldsa44_verify(pk, sizeof pk, msg, sizeof msg - 1U,
                                 ctx, sizeof ctx - 1U, sig, sizeof sig))
            return 4;
        mldsa_shake_absorb(&transcript, sig, sizeof sig);
    }
    for (unsigned i = 0; i < BENCH_SAMPLES; i++) {
        uint32_t mark = physical_stack_fill();
        uint32_t t = physical_cycles();
        int rc = mldsa44_verify(pk, sizeof pk, msg, sizeof msg - 1U,
                                ctx, sizeof ctx - 1U, sig, sizeof sig);
        uint32_t end = physical_cycles();
        raw[5][i] = end - t;
        stacks[3][i] = physical_stack_used(mark);
        if (rc)
            return 5;
    }
    emit(correction);
    return 0;
}
