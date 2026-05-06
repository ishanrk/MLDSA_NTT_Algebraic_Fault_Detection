#include "mldsa44.h"
#include "mldsa44_internal.h"
#include "mldsa_shake.h"

#include <string.h>

void mldsa44_keygen(uint8_t pk[MLDSA44_PUBLICKEY_BYTES],
                    uint8_t sk[MLDSA44_SECRETKEY_BYTES],
                    const uint8_t seed[MLDSA44_SEED_BYTES])
{
    uint8_t in[34], expanded[128], tr[64];
    mldsa_ntt a[4][4], s1ntt[4];
    mldsa_poly s1[4], s2[4], t[4], t1[4], t0[4];

    memcpy(in, seed, 32);
    in[32] = 4;
    in[33] = 4;
    mldsa_shake256(expanded, sizeof expanded, in, sizeof in);
    mldsa44_expand_a(a, expanded);
    mldsa44_expand_s(s1, s2, expanded + 32);
    for (unsigned i = 0; i < 4; i++)
        mldsa_ntt_forward(&s1ntt[i], &s1[i]);
    mldsa44_matvec(t, a, s1ntt);

    for (unsigned i = 0; i < 4; i++) {
        for (unsigned j = 0; j < MLDSA_N; j++) {
            uint32_t hi;
            int32_t lo;
            t[i].c[j] = mldsa_add(t[i].c[j], s2[i].c[j]);
            mldsa44_power2round(t[i].c[j], &hi, &lo);
            t1[i].c[j] = hi;
            t0[i].c[j] = mldsa_uncenter(lo);
        }
    }
    mldsa44_pk_encode(pk, expanded, t1);
    mldsa_shake256(tr, sizeof tr, pk, MLDSA44_PUBLICKEY_BYTES);
    mldsa44_sk_encode(sk, expanded, expanded + 96, tr, s1, s2, t0);
}
