#include "mldsa44.h"
#include "mldsa44_internal.h"
#include "mldsa_shake.h"

#include <string.h>

static int sign_core(uint8_t sig[MLDSA44_SIGNATURE_BYTES],
                     const uint8_t *sk, size_t sklen,
                     unsigned hash, const uint8_t *msg, size_t mlen,
                     const uint8_t *ctx, size_t clen,
                     const uint8_t rnd[MLDSA44_RANDOM_BYTES])
{
    uint8_t rho[32], key[32], tr[64], mu[64], rhopp[64], in[128];
    uint8_t ctilde[32], w1bytes[MLDSA44_W1_BYTES], h[4][256];
    mldsa_ntt a[4][4], s1n[4], s2n[4], t0n[4];
    mldsa_ntt yn[4], cn;
    mldsa_poly s1[4], s2[4], t0[4], y[4], w[4], w1[4];
    mldsa_poly z[4], r[4], cs1[4], cs2[4], ct0[4], c;

    if (sig == NULL || sk == NULL || rnd == NULL ||
        sklen != MLDSA44_SECRETKEY_BYTES || clen > 255U ||
        (mlen && msg == NULL) || (clen && ctx == NULL))
        return -1;
    if (mldsa44_sk_decode(rho, key, tr, s1, s2, t0, sk))
        return -1;
    mldsa44_expand_a(a, rho);
    for (unsigned i = 0; i < 4; i++) {
        mldsa_ntt_forward(&s1n[i], &s1[i]);
        mldsa_ntt_forward(&s2n[i], &s2[i]);
        mldsa_ntt_forward(&t0n[i], &t0[i]);
    }
    mldsa44_representative(mu, tr, hash, msg, mlen, ctx, clen);
    memcpy(in, key, 32);
    memcpy(in + 32, rnd, 32);
    memcpy(in + 64, mu, 64);
    mldsa_shake256(rhopp, 64, in, sizeof in);

    for (uint32_t nonce = 0;; nonce += 4U) {
        mldsa_shake s;
        unsigned weight = 0;
        int reject = 0;

        mldsa44_expand_mask(y, rhopp, nonce);
        for (unsigned i = 0; i < 4; i++)
            mldsa_ntt_forward(&yn[i], &y[i]);
        mldsa44_matvec(w, a, yn);
        for (unsigned i = 0; i < 4; i++) {
            for (unsigned j = 0; j < MLDSA_N; j++)
                w1[i].c[j] = mldsa44_highbits(w[i].c[j]);
        }
        mldsa44_w1_encode(w1bytes, w1);
        mldsa_shake_init(&s, 256);
        mldsa_shake_absorb(&s, mu, 64);
        mldsa_shake_absorb(&s, w1bytes, sizeof w1bytes);
        mldsa_shake_squeeze(&s, ctilde, 32);
        mldsa44_sample_ball(&c, ctilde);
        mldsa_ntt_forward(&cn, &c);
        for (unsigned i = 0; i < 4; i++) {
            mldsa44_mul_ntt(&cs1[i], &cn, &s1n[i]);
            mldsa44_mul_ntt(&cs2[i], &cn, &s2n[i]);
            mldsa_poly_add(&z[i], &y[i], &cs1[i]);
            mldsa_poly_sub(&r[i], &w[i], &cs2[i]);
            reject |= mldsa44_norm(&z[i], MLDSA44_GAMMA1 - MLDSA44_BETA);
            for (unsigned j = 0; j < MLDSA_N; j++) {
                int32_t x = mldsa44_lowbits(r[i].c[j]);
                if (x < 0)
                    x = -x;
                reject |= x >= MLDSA44_GAMMA2 - MLDSA44_BETA;
            }
        }
        if (reject)
            continue;

        for (unsigned i = 0; i < 4; i++) {
            mldsa44_mul_ntt(&ct0[i], &cn, &t0n[i]);
            for (unsigned j = 0; j < MLDSA_N; j++) {
                uint32_t v = mldsa_add(r[i].c[j], ct0[i].c[j]);
                uint32_t neg = mldsa_sub(0U, ct0[i].c[j]);
                h[i][j] = mldsa44_make_hint(neg, v);
                weight += h[i][j];
            }
        }
        for (unsigned i = 0; i < 4; i++)
            reject |= mldsa44_norm(&ct0[i], MLDSA44_GAMMA2);
        if (reject || weight > MLDSA44_OMEGA)
            continue;
        return mldsa44_sig_encode(sig, ctilde, z, h);
    }
}

int mldsa44_sign(uint8_t sig[MLDSA44_SIGNATURE_BYTES],
                 const uint8_t *sk, size_t sklen,
                 const uint8_t *msg, size_t mlen,
                 const uint8_t *ctx, size_t clen,
                 const uint8_t rnd[MLDSA44_RANDOM_BYTES])
{
    return sign_core(sig, sk, sklen, 0, msg, mlen, ctx, clen, rnd);
}

int mldsa44_sign_digest(uint8_t sig[MLDSA44_SIGNATURE_BYTES],
                        const uint8_t *sk, size_t sklen,
                        unsigned hash, const uint8_t *digest, size_t dlen,
                        const uint8_t *ctx, size_t clen,
                        const uint8_t rnd[MLDSA44_RANDOM_BYTES])
{
    if (dlen == 0U || dlen != mldsa44_digest_len(hash))
        return -1;
    return sign_core(sig, sk, sklen, hash, digest, dlen, ctx, clen, rnd);
}
