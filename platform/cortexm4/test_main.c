#include "mldsa44.h"
#include "mldsa_poly.h"
#include "mldsa_shake.h"
#include "platform.h"
#ifdef MLDSA_PRIOR_CHECKER
#include "prior_cases.h"
#endif

#include <stdint.h>

#include "mps2_vectors.inc"

static uint8_t pk[MLDSA44_PUBLICKEY_BYTES], sk[MLDSA44_SECRETKEY_BYTES];
static uint8_t sig[MLDSA44_SIGNATURE_BYTES], raw[MLDSA_N * 4U];
static mldsa_poly a, back;
static mldsa_ntt an;

static int same(const uint8_t *x, const uint8_t *y, unsigned n)
{
    unsigned diff = 0;
    for (unsigned i = 0; i < n; i++)
        diff |= (unsigned)(x[i] ^ y[i]);
    return diff == 0U;
}

static int hash_matches(const uint8_t *data, unsigned n, const uint8_t want[32])
{
    uint8_t out[32];
    mldsa_shake256(out, 32, data, n);
    return same(out, want, 32);
}

static int check_ntt(const uint8_t want[32])
{
    mldsa_ntt_forward(&an, &a);
    for (unsigned i = 0; i < MLDSA_N; i++) {
        for (unsigned j = 0; j < 4; j++)
            raw[4U * i + j] = (uint8_t)(an.c[i] >> (8U * j));
    }
    if (!hash_matches(raw, sizeof raw, want))
        return 0;
    mldsa_ntt_inverse(&back, &an);
    for (unsigned i = 0; i < MLDSA_N; i++) {
        if (back.c[i] != a.c[i])
            return 0;
    }
    return 1;
}

int main(void)
{
    uint8_t out[sizeof kat_shake], rnd[32];
    uint8_t msg[] = "Cortex M4 portable baseline";
    const uint8_t ctx[] = "arm";
    uint32_t x = 20446U;

#ifdef MLDSA_PRIOR_CHECKER
    int rc = test_prior();
    if (rc)
        return 20 + rc;
#endif
    mldsa_shake256(out, sizeof out, kat_shake_msg, sizeof kat_shake_msg);
    if (!same(out, kat_shake, sizeof out))
        return 1;
    platform_write("SHAKE PASS\n");

    if (!check_ntt(kat_ntt_zero))
        return 2;
    platform_write("NTT zero PASS\n");
    a.c[1] = 1U;
    if (!check_ntt(kat_ntt_basis))
        return 3;
    platform_write("NTT basis PASS\n");
    for (unsigned i = 0; i < MLDSA_N; i++)
        a.c[i] = i % 2U ? MLDSA_Q - 1U : 0U;
    if (!check_ntt(kat_ntt_boundary))
        return 4;
    platform_write("NTT boundary PASS\n");
    for (unsigned i = 0; i < MLDSA_N; i++) {
        x = x * 1664525U + 1013904223U;
        a.c[i] = x % MLDSA_Q;
    }
    if (!check_ntt(kat_ntt_random))
        return 5;
    platform_write("NTT fixed random PASS\n");

    if (mldsa44_keygen(pk, sk, kat_seed) ||
        !hash_matches(pk, sizeof pk, kat_pk) ||
        !hash_matches(sk, sizeof sk, kat_sk))
        return 6;
    platform_write("KEYGEN PASS\n");
    for (unsigned i = 0; i < 32; i++)
        rnd[i] = (uint8_t)i;
    if (mldsa44_sign(sig, sk, sizeof sk, msg, sizeof msg - 1U,
                     ctx, sizeof ctx - 1U, rnd) ||
        !hash_matches(sig, sizeof sig, kat_sig))
        return 7;
    platform_write("SIGN PASS\n");
    if (mldsa44_verify(pk, sizeof pk, msg, sizeof msg - 1U,
                       ctx, sizeof ctx - 1U, sig, sizeof sig))
        return 8;
    platform_write("VERIFY valid PASS\n");
    msg[0] ^= 1U;
    if (!mldsa44_verify(pk, sizeof pk, msg, sizeof msg - 1U,
                        ctx, sizeof ctx - 1U, sig, sizeof sig))
        return 9;
    platform_write("VERIFY modified message PASS\n");
    msg[0] ^= 1U;
    sig[0] ^= 1U;
    if (!mldsa44_verify(pk, sizeof pk, msg, sizeof msg - 1U,
                        ctx, sizeof ctx - 1U, sig, sizeof sig))
        return 10;
    platform_write("VERIFY modified signature PASS\n");
#ifdef MLDSA_PRIOR_CHECKER
    sig[0] ^= 1U;
    test_prior_inject(1, 1152, 17);
    if (mldsa44_verify(pk, sizeof pk, msg, sizeof msg - 1U,
                       ctx, sizeof ctx - 1U, sig, sizeof sig) != -1)
        return 11;
    test_prior_inject(1, 1152, 17);
    if (mldsa44_sign(sig, sk, sizeof sk, msg, sizeof msg - 1U,
                     ctx, sizeof ctx - 1U, rnd) != -1)
        return 12;
    test_prior_inject(1, 1152, 17);
    if (mldsa44_keygen(pk, sk, kat_seed) != -1)
        return 13;
    test_prior_inject(0, 0, 0);
    platform_write("PRIOR scheme fault propagation PASS\n");
#endif
    return 0;
}
