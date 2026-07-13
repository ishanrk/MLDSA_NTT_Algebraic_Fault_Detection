#ifndef MLDSA44_INTERNAL_H
#define MLDSA44_INTERNAL_H

#include "mldsa_poly.h"
#if defined(MLDSA_PRIOR_CHECKER) || defined(MLDSA_OUR_CHECKER)
#include "mldsa_checker.h"
#endif
#if defined(MLDSA_PRIOR_CHECKER) && defined(MLDSA_OUR_CHECKER)
#error Select one NTT checker
#endif
#include <stddef.h>

static inline int mldsa44_ntt(mldsa_ntt *r, const mldsa_poly *a)
{
#ifdef MLDSA_PRIOR_CHECKER
    return mldsa_ntt_forward_prior(r, a);
#elif defined(MLDSA_OUR_CHECKER)
    return mldsa_ntt_forward_our(r, a);
#else
    mldsa_ntt_forward(r, a);
    return 0;
#endif
}

enum {
    MLDSA44_K = 4,
    MLDSA44_L = 4,
    MLDSA44_D = 13,
    MLDSA44_ETA = 2,
    MLDSA44_TAU = 39,
    MLDSA44_BETA = 78,
    MLDSA44_GAMMA1 = 131072,
    MLDSA44_GAMMA2 = 95232,
    MLDSA44_OMEGA = 80,
    MLDSA44_ALPHA = 190464,
    MLDSA44_PK_BYTES = 1312,
    MLDSA44_SK_BYTES = 2560,
    MLDSA44_SIG_BYTES = 2420,
    MLDSA44_W1_BYTES = 768
};

void mldsa44_power2round(uint32_t r, uint32_t *hi, int32_t *lo);
void mldsa44_decompose(uint32_t r, uint32_t *hi, int32_t *lo);
uint32_t mldsa44_highbits(uint32_t r);
int32_t mldsa44_lowbits(uint32_t r);
uint8_t mldsa44_make_hint(uint32_t z, uint32_t r);
uint32_t mldsa44_use_hint(uint8_t h, uint32_t r);
int mldsa44_norm(const mldsa_poly *a, uint32_t bound);
int mldsa44_unpack_bits(mldsa_poly *a, const uint8_t *in, unsigned bits,
                        int32_t top, uint32_t max, int signed_coeff);
void mldsa44_expand_a(mldsa_ntt a[4][4], const uint8_t rho[32]);
void mldsa44_expand_s(mldsa_poly s1[4], mldsa_poly s2[4], const uint8_t rho[64]);
void mldsa44_expand_mask(mldsa_poly y[4], const uint8_t rho[64], uint32_t nonce);
void mldsa44_sample_ball(mldsa_poly *c, const uint8_t seed[32]);
void mldsa44_matvec(mldsa_poly out[4], mldsa_ntt a[4][4], const mldsa_ntt v[4]);
void mldsa44_mul_ntt(mldsa_poly *out, const mldsa_ntt *a, const mldsa_ntt *b);

void mldsa44_pk_encode(uint8_t out[MLDSA44_PK_BYTES], const uint8_t rho[32],
                       const mldsa_poly t1[4]);
void mldsa44_pk_decode(uint8_t rho[32], mldsa_poly t1[4],
                       const uint8_t in[MLDSA44_PK_BYTES]);
void mldsa44_sk_encode(uint8_t out[MLDSA44_SK_BYTES], const uint8_t rho[32],
                       const uint8_t key[32], const uint8_t tr[64],
                       const mldsa_poly s1[4], const mldsa_poly s2[4],
                       const mldsa_poly t0[4]);
int mldsa44_sk_decode(uint8_t rho[32], uint8_t key[32], uint8_t tr[64],
                      mldsa_poly s1[4], mldsa_poly s2[4], mldsa_poly t0[4],
                      const uint8_t in[MLDSA44_SK_BYTES]);
int mldsa44_sig_encode(uint8_t out[MLDSA44_SIG_BYTES], const uint8_t c[32],
                       const mldsa_poly z[4], uint8_t h[4][256]);
int mldsa44_sig_decode(uint8_t c[32], mldsa_poly z[4], uint8_t h[4][256],
                       const uint8_t in[MLDSA44_SIG_BYTES]);
void mldsa44_w1_encode(uint8_t out[MLDSA44_W1_BYTES], const mldsa_poly w1[4]);
size_t mldsa44_digest_len(unsigned hash);
void mldsa44_representative(uint8_t mu[64], const uint8_t tr[64],
                            unsigned hash,
                            const uint8_t *msg, size_t mlen,
                            const uint8_t *ctx, size_t clen);

#endif
