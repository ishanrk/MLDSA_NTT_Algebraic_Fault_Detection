#include "mldsa44_internal.h"

#include <string.h>

static void pack(uint8_t *out, const mldsa_poly *a, unsigned bits,
                 int32_t top, int signed_coeff)
{
    memset(out, 0, 32U * bits);
    for (unsigned i = 0; i < MLDSA_N; i++) {
        uint32_t v = (uint32_t)(signed_coeff ? top - mldsa_center(a->c[i]) :
                                             (int32_t)a->c[i]);
        for (unsigned j = 0; j < bits; j++) {
            unsigned pos = i * bits + j;
            out[pos / 8U] |= (uint8_t)(((v >> j) & 1U) << (pos % 8U));
        }
    }
}

int mldsa44_unpack_bits(mldsa_poly *a, const uint8_t *in, unsigned bits,
                        int32_t top, uint32_t max, int signed_coeff)
{
    for (unsigned i = 0; i < MLDSA_N; i++) {
        uint32_t v = 0;
        for (unsigned j = 0; j < bits; j++) {
            unsigned pos = i * bits + j;
            v |= (((uint32_t)in[pos / 8U] >> (pos % 8U)) & 1U) << j;
        }
        if (v > max)
            return -1;
        a->c[i] = signed_coeff ? mldsa_uncenter(top - (int32_t)v) : v;
    }
    return 0;
}

void mldsa44_pk_encode(uint8_t out[MLDSA44_PK_BYTES], const uint8_t rho[32],
                       const mldsa_poly t1[4])
{
    memcpy(out, rho, 32);
    for (unsigned i = 0; i < 4; i++)
        pack(out + 32U + 320U * i, &t1[i], 10, 0, 0);
}

void mldsa44_pk_decode(uint8_t rho[32], mldsa_poly t1[4],
                       const uint8_t in[MLDSA44_PK_BYTES])
{
    memcpy(rho, in, 32);
    for (unsigned i = 0; i < 4; i++)
        (void)mldsa44_unpack_bits(&t1[i], in + 32U + 320U * i, 10, 0, 1023U, 0);
}

void mldsa44_sk_encode(uint8_t out[MLDSA44_SK_BYTES], const uint8_t rho[32],
                       const uint8_t key[32], const uint8_t tr[64],
                       const mldsa_poly s1[4], const mldsa_poly s2[4],
                       const mldsa_poly t0[4])
{
    memcpy(out, rho, 32);
    memcpy(out + 32, key, 32);
    memcpy(out + 64, tr, 64);
    for (unsigned i = 0; i < 4; i++) {
        pack(out + 128U + 96U * i, &s1[i], 3, 2, 1);
        pack(out + 512U + 96U * i, &s2[i], 3, 2, 1);
        pack(out + 896U + 416U * i, &t0[i], 13, 4096, 1);
    }
}

int mldsa44_sk_decode(uint8_t rho[32], uint8_t key[32], uint8_t tr[64],
                      mldsa_poly s1[4], mldsa_poly s2[4], mldsa_poly t0[4],
                      const uint8_t in[MLDSA44_SK_BYTES])
{
    memcpy(rho, in, 32);
    memcpy(key, in + 32, 32);
    memcpy(tr, in + 64, 64);
    for (unsigned i = 0; i < 4; i++) {
        if (mldsa44_unpack_bits(&s1[i], in + 128U + 96U * i, 3, 2, 4U, 1) ||
            mldsa44_unpack_bits(&s2[i], in + 512U + 96U * i, 3, 2, 4U, 1) ||
            mldsa44_unpack_bits(&t0[i], in + 896U + 416U * i, 13, 4096, 8191U, 1))
            return -1;
    }
    return 0;
}

int mldsa44_sig_encode(uint8_t out[MLDSA44_SIG_BYTES], const uint8_t c[32],
                       const mldsa_poly z[4], uint8_t h[4][256])
{
    unsigned n = 0;
    uint8_t *tail = out + 2336;

    memcpy(out, c, 32);
    for (unsigned i = 0; i < 4; i++)
        pack(out + 32U + 576U * i, &z[i], 18, 131072, 1);
    memset(tail, 0, 84);
    for (unsigned i = 0; i < 4; i++) {
        for (unsigned j = 0; j < MLDSA_N; j++) {
            if (h[i][j]) {
                if (n == MLDSA44_OMEGA)
                    return -1;
                tail[n++] = (uint8_t)j;
            }
        }
        tail[MLDSA44_OMEGA + i] = (uint8_t)n;
    }
    return 0;
}

int mldsa44_sig_decode(uint8_t c[32], mldsa_poly z[4], uint8_t h[4][256],
                       const uint8_t in[MLDSA44_SIG_BYTES])
{
    const uint8_t *tail = in + 2336;
    unsigned n = 0;

    memcpy(c, in, 32);
    for (unsigned i = 0; i < 4; i++)
        (void)mldsa44_unpack_bits(&z[i], in + 32U + 576U * i, 18, 131072, 262143U, 1);
    memset(h, 0, 4U * 256U);
    for (unsigned i = 0; i < 4; i++) {
        unsigned end = tail[MLDSA44_OMEGA + i];
        if (end < n || end > MLDSA44_OMEGA)
            return -1;
        for (unsigned j = n; j < end; j++) {
            if (j > n && tail[j] <= tail[j - 1U])
                return -1;
            h[i][tail[j]] = 1;
        }
        n = end;
    }
    for (unsigned i = n; i < MLDSA44_OMEGA; i++) {
        if (tail[i] != 0U)
            return -1;
    }
    return 0;
}

void mldsa44_w1_encode(uint8_t out[MLDSA44_W1_BYTES], const mldsa_poly w1[4])
{
    for (unsigned i = 0; i < 4; i++)
        pack(out + 192U * i, &w1[i], 6, 0, 0);
}
