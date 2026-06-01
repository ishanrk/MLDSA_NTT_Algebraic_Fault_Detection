#include "mldsa44_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t state = 20445U;

static uint32_t rand32(void)
{
    state = state * 1664525U + 1013904223U;
    return state;
}

static void same(const mldsa_poly a[4], const mldsa_poly b[4])
{
    if (memcmp(a, b, 4U * sizeof *a) != 0)
        abort();
}

int main(void)
{
    uint8_t rho[32], key[32], tr[64], c[32];
    uint8_t rho2[32], key2[32], tr2[64], c2[32];
    uint8_t pk[MLDSA44_PK_BYTES], sk[MLDSA44_SK_BYTES];
    uint8_t sig[MLDSA44_SIG_BYTES], w1bytes[MLDSA44_W1_BYTES];
    uint8_t h[4][256] = {{0}}, h2[4][256];
    mldsa_poly t1[4], t12[4], s1[4], s2[4], t0[4];
    mldsa_poly s12[4], s22[4], t02[4], z[4], z2[4], w1[4];

    for (unsigned i = 0; i < 32; i++) {
        rho[i] = (uint8_t)rand32();
        key[i] = (uint8_t)rand32();
        c[i] = (uint8_t)rand32();
    }
    for (unsigned i = 0; i < 64; i++)
        tr[i] = (uint8_t)rand32();
    for (unsigned i = 0; i < 4; i++) {
        for (unsigned j = 0; j < MLDSA_N; j++) {
            t1[i].c[j] = rand32() % 1024U;
            s1[i].c[j] = mldsa_uncenter((int32_t)(rand32() % 5U) - 2);
            s2[i].c[j] = mldsa_uncenter((int32_t)(rand32() % 5U) - 2);
            t0[i].c[j] = mldsa_uncenter((int32_t)(rand32() % 8192U) - 4095);
            z[i].c[j] = mldsa_uncenter((int32_t)(rand32() % 262144U) - 131071);
            w1[i].c[j] = rand32() % 44U;
        }
        for (unsigned j = 0; j < 10; j++)
            h[i][j * 17U] = 1;
    }

    mldsa44_pk_encode(pk, rho, t1);
    mldsa44_pk_decode(rho2, t12, pk);
    if (memcmp(rho, rho2, 32) != 0)
        abort();
    same(t1, t12);

    mldsa44_sk_encode(sk, rho, key, tr, s1, s2, t0);
    if (mldsa44_sk_decode(rho2, key2, tr2, s12, s22, t02, sk))
        abort();
    if (memcmp(rho, rho2, 32) || memcmp(key, key2, 32) || memcmp(tr, tr2, 64))
        abort();
    same(s1, s12);
    same(s2, s22);
    same(t0, t02);
    sk[128] = (uint8_t)((sk[128] & 0xf8U) | 7U);
    if (!mldsa44_sk_decode(rho2, key2, tr2, s12, s22, t02, sk))
        abort();

    if (mldsa44_sig_encode(sig, c, z, h))
        abort();
    if (mldsa44_sig_decode(c2, z2, h2, sig))
        abort();
    if (memcmp(c, c2, 32) || memcmp(h, h2, sizeof h))
        abort();
    same(z, z2);
    sig[2336U + 80U] = 81;
    if (!mldsa44_sig_decode(c2, z2, h2, sig))
        abort();
    sig[2336U + 80U] = 10;
    sig[2336U + 1U] = sig[2336U];
    if (!mldsa44_sig_decode(c2, z2, h2, sig))
        abort();
    sig[2336U + 1U] = 17;
    sig[2336U + 40U] = 1;
    if (!mldsa44_sig_decode(c2, z2, h2, sig))
        abort();

    mldsa44_w1_encode(w1bytes, w1);
    for (unsigned i = 0; i < 4; i++) {
        for (unsigned j = 0; j < MLDSA_N; j++) {
            uint32_t v = 0;
            for (unsigned k = 0; k < 6; k++) {
                unsigned pos = j * 6U + k;
                v |= (((uint32_t)w1bytes[192U * i + pos / 8U] >> (pos % 8U)) & 1U) << k;
            }
            if (v != w1[i].c[j])
                abort();
        }
    }
    puts("key signature and w1 encoding passed");
    return EXIT_SUCCESS;
}
