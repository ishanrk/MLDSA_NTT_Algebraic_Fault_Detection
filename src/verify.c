#include "mldsa44.h"
#include "mldsa44_internal.h"
#include "mldsa_shake.h"

int mldsa44_verify(const uint8_t *pk, size_t pklen,
                   const uint8_t *msg, size_t mlen,
                   const uint8_t *ctx, size_t clen,
                   const uint8_t *sig, size_t siglen)
{
    uint8_t rho[32], tr[64], mu[64], ctilde[32], check[32];
    uint8_t w1bytes[MLDSA44_W1_BYTES], h[4][256];
    mldsa_ntt a[4][4], zn[4], cn;
    mldsa_poly t1[4], z[4], w[4], w1[4], c, ct1;
    unsigned diff = 0;

    if (pk == NULL || sig == NULL || pklen != MLDSA44_PUBLICKEY_BYTES ||
        siglen != MLDSA44_SIGNATURE_BYTES || clen > 255U ||
        (mlen && msg == NULL) || (clen && ctx == NULL))
        return -1;
    mldsa44_pk_decode(rho, t1, pk);
    if (mldsa44_sig_decode(ctilde, z, h, sig))
        return -1;
    for (unsigned i = 0; i < 4; i++) {
        if (mldsa44_norm(&z[i], MLDSA44_GAMMA1 - MLDSA44_BETA))
            return -1;
    }
    mldsa_shake256(tr, 64, pk, pklen);
    mldsa44_representative(mu, tr, msg, mlen, ctx, clen);
    mldsa44_sample_ball(&c, ctilde);
    mldsa_ntt_forward(&cn, &c);
    mldsa44_expand_a(a, rho);
    for (unsigned i = 0; i < 4; i++)
        mldsa_ntt_forward(&zn[i], &z[i]);
    mldsa44_matvec(w, a, zn);
    for (unsigned i = 0; i < 4; i++) {
        for (unsigned j = 0; j < MLDSA_N; j++)
            t1[i].c[j] = mldsa_mul(t1[i].c[j], 1U << MLDSA44_D);
        mldsa_ntt tn;
        mldsa_ntt_forward(&tn, &t1[i]);
        mldsa44_mul_ntt(&ct1, &cn, &tn);
        for (unsigned j = 0; j < MLDSA_N; j++) {
            uint32_t v = mldsa_sub(w[i].c[j], ct1.c[j]);
            w1[i].c[j] = mldsa44_use_hint(h[i][j], v);
        }
    }
    mldsa44_w1_encode(w1bytes, w1);
    mldsa_shake s;
    mldsa_shake_init(&s, 256);
    mldsa_shake_absorb(&s, mu, 64);
    mldsa_shake_absorb(&s, w1bytes, sizeof w1bytes);
    mldsa_shake_squeeze(&s, check, 32);
    for (unsigned i = 0; i < 32; i++)
        diff |= (unsigned)(ctilde[i] ^ check[i]);
    return diff ? -1 : 0;
}
