#include "mldsa44.h"
#include "mldsa_checker.h"
#include "mldsa_poly.h"
#include "mldsa_shake.h"
#include "platform.h"

#include <stdint.h>
#include <string.h>

#ifndef QEMU_SAMPLES
#define QEMU_SAMPLES 101
#endif

static mldsa_poly a, b, back;
static mldsa_ntt an, bn, out, expected;
static uint8_t pk[MLDSA44_PUBLICKEY_BYTES], sk[MLDSA44_SECRETKEY_BYTES];
static uint8_t sig[MLDSA44_SIGNATURE_BYTES];
static const char *const operations[] = {
    "ntt_forward", "ntt_inverse", "pointwise", "keygen", "sign", "verify"
};

__attribute__((noinline, noclone, used, externally_visible))
void benchmark_begin(void)
{
    __asm volatile("nop" ::: "memory");
}

__attribute__((noinline, noclone, used, externally_visible))
void benchmark_end(void)
{
    __asm volatile("nop\n\tnop" ::: "memory");
}

static void number(unsigned n)
{
    char buffer[12];
    unsigned i = sizeof buffer - 1U;
    buffer[i] = '\0';
    do {
        buffer[--i] = (char)('0' + n % 10U);
        n /= 10U;
    } while (n);
    platform_write(buffer + i);
}

static void label(const char *operation, unsigned sample, unsigned interval)
{
    platform_write("{\"kind\":\"region\",\"op\":\"");
    platform_write(operation);
    platform_write("\",\"sample\":");
    number(sample);
    platform_write(",\"interval\":");
    number(interval);
    platform_write("}\n");
}

static int forward(mldsa_ntt *r, const mldsa_poly *p)
{
#if defined(MLDSA_PRIOR_CHECKER)
    return mldsa_ntt_forward_prior(r, p);
#elif defined(MLDSA_OUR_CHECKER)
    return mldsa_ntt_forward_our(r, p);
#else
    mldsa_ntt_forward(r, p);
    return 0;
#endif
}

int main(void)
{
    const uint8_t message[] = "Cortex M4 portable baseline";
    const uint8_t context[] = "arm";
    uint8_t seed[32], rnd[32] = {0}, digest[32];
    mldsa_shake transcript;
    unsigned interval = 0;
    __asm volatile("cpsid i" ::: "memory");
    *(volatile uint32_t *)0xe000e010U = 0;
    __asm volatile("bl benchmark_begin\n\tbl benchmark_end"
                   ::: "r0", "r1", "r2", "r3", "r12", "lr", "cc", "memory");
    label("control_empty", 0, interval++);
    __asm volatile("bl benchmark_begin\n\tmovs r2, #100\n1:\n\tnop\n\tsubs r2, #1\n\tbne 1b\n\tbl benchmark_end"
                   ::: "r0", "r1", "r2", "r3", "r12", "lr", "cc", "memory");
    label("control_loop", 0, interval++);
    for (unsigned i = 0; i < QEMU_SAMPLES; i++) {
        benchmark_begin();
        benchmark_end();
        label("overhead", i, interval++);
    }
    for (unsigned i = 0; i < MLDSA_N; i++) {
        a.c[i] = ((i + 1U) * (i + 17U)) % MLDSA_Q;
        b.c[i] = ((3U * i + 2U) * (7U * i + 5U)) % MLDSA_Q;
    }
    mldsa_ntt_forward(&expected, &a);
    if (forward(&an, &a) || forward(&bn, &b))
        return 1;
    mldsa_shake_init(&transcript, 256);
    for (unsigned i = 0; i < QEMU_SAMPLES; i++) {
        benchmark_begin();
        int rc = forward(&out, &a);
        benchmark_end();
        if (rc || memcmp(&out, &expected, sizeof out))
            return 2;
        label(operations[0], i, interval++);
    }
    for (unsigned i = 0; i < QEMU_SAMPLES; i++) {
        benchmark_begin();
        mldsa_ntt_inverse(&back, &an);
        benchmark_end();
        if (memcmp(&back, &a, sizeof back))
            return 3;
        label(operations[1], i, interval++);
    }
    mldsa_ntt_mul(&expected, &an, &bn);
    for (unsigned i = 0; i < QEMU_SAMPLES; i++) {
        benchmark_begin();
        mldsa_ntt_mul(&out, &an, &bn);
        benchmark_end();
        if (memcmp(&out, &expected, sizeof out))
            return 4;
        label(operations[2], i, interval++);
    }
    for (unsigned i = 0; i < 32; i++)
        seed[i] = (uint8_t)i;
    for (unsigned i = 0; i < QEMU_SAMPLES; i++) {
        seed[0] = (uint8_t)i;
        benchmark_begin();
        int rc = mldsa44_keygen(pk, sk, seed);
        benchmark_end();
        if (rc)
            return 5;
        mldsa_shake_absorb(&transcript, pk, sizeof pk);
        label(operations[3], i, interval++);
    }
    seed[0] = 0;
    if (mldsa44_keygen(pk, sk, seed))
        return 6;
    for (unsigned i = 0; i < QEMU_SAMPLES; i++) {
        rnd[0] = (uint8_t)i;
        benchmark_begin();
        int rc = mldsa44_sign(sig, sk, sizeof sk, message, sizeof message - 1U,
                              context, sizeof context - 1U, rnd);
        benchmark_end();
        if (rc || mldsa44_verify(pk, sizeof pk, message, sizeof message - 1U,
                                 context, sizeof context - 1U, sig, sizeof sig))
            return 7;
        mldsa_shake_absorb(&transcript, sig, sizeof sig);
        label(operations[4], i, interval++);
    }
    for (unsigned i = 0; i < QEMU_SAMPLES; i++) {
        benchmark_begin();
        int rc = mldsa44_verify(pk, sizeof pk, message, sizeof message - 1U,
                                context, sizeof context - 1U, sig, sizeof sig);
        benchmark_end();
        if (rc)
            return 8;
        label(operations[5], i, interval++);
    }
    mldsa_shake_squeeze(&transcript, digest, sizeof digest);
    platform_write("{\"kind\":\"result\",\"variant\":\"" QEMU_VARIANT
                   "\",\"transcript_shake256\":\"");
    for (unsigned i = 0; i < sizeof digest; i++) {
        static const char hex[] = "0123456789abcdef";
        char byte[] = {hex[digest[i] >> 4], hex[digest[i] & 15U], 0};
        platform_write(byte);
    }
    platform_write("\",\"status\":\"passed\"}\n");
    return 0;
}
