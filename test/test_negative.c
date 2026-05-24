#include "mldsa44.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t state = 20446U;
static unsigned cases;

static uint32_t rand32(void)
{
    state = state * 1664525U + 1013904223U;
    return state;
}

static void bad(const uint8_t *pk, size_t pklen, const uint8_t *msg,
                size_t mlen, const uint8_t *ctx, size_t clen,
                const uint8_t *sig, size_t siglen)
{
    if (mldsa44_verify(pk, pklen, msg, mlen, ctx, clen, sig, siglen) == 0)
        abort();
    cases++;
}

int main(void)
{
    uint8_t seed[32], rnd[32], pk[MLDSA44_PUBLICKEY_BYTES];
    uint8_t sk[MLDSA44_SECRETKEY_BYTES], sig[MLDSA44_SIGNATURE_BYTES];
    uint8_t tmp[MLDSA44_SIGNATURE_BYTES + 1U];
    uint8_t key[MLDSA44_PUBLICKEY_BYTES];
    uint8_t msg[] = {1, 2, 3, 4, 5};
    uint8_t ctx[] = {6, 7, 8};

    for (unsigned i = 0; i < 32; i++) {
        seed[i] = (uint8_t)rand32();
        rnd[i] = (uint8_t)rand32();
    }
    mldsa44_keygen(pk, sk, seed);
    if (mldsa44_sign(sig, sk, sizeof sk, msg, sizeof msg,
                     ctx, sizeof ctx, rnd) ||
        mldsa44_verify(pk, sizeof pk, msg, sizeof msg,
                       ctx, sizeof ctx, sig, sizeof sig))
        abort();

    msg[0] ^= 1U;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);
    msg[0] ^= 1U;
    ctx[0] ^= 1U;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);
    ctx[0] ^= 1U;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, 0, sig, sizeof sig);
    bad(pk, sizeof pk, msg, sizeof msg - 1U, ctx, sizeof ctx, sig, sizeof sig);

    for (unsigned i = 0; i < sizeof pk; i += 17U) {
        memcpy(key, pk, sizeof key);
        key[i] ^= 1U;
        bad(key, sizeof key, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);
    }
    for (unsigned i = 0; i < sizeof sig; i += 19U) {
        memcpy(tmp, sig, sizeof sig);
        tmp[i] ^= 1U;
        bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
    }
    for (unsigned i = 0; i < 50U; i++) {
        memcpy(tmp, sig, sizeof sig);
        for (unsigned j = 0; j < 1U + i % 8U; j++)
            tmp[rand32() % sizeof sig] ^= (uint8_t)(1U << (rand32() % 8U));
        bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
    }

    bad(pk, sizeof pk - 1U, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);
    bad(pk, 0, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);
    bad(pk, sizeof pk + 1U, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig - 1U);
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, sig, 0);
    memcpy(tmp, sig, sizeof sig);
    tmp[sizeof sig] = 0;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof tmp);
    bad(NULL, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, NULL, sizeof sig);
    bad(pk, sizeof pk, NULL, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);
    bad(pk, sizeof pk, msg, sizeof msg, NULL, sizeof ctx, sig, sizeof sig);
    bad(pk, sizeof pk, msg, sizeof msg, ctx, 256U, sig, sizeof sig);

    memcpy(tmp, sig, sizeof sig);
    tmp[0] ^= 1U;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
    memcpy(tmp, sig, sizeof sig);
    tmp[32] = 0;
    tmp[33] = 0;
    tmp[34] &= 0xfcU;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
    memcpy(tmp, sig, sizeof sig);
    tmp[32] = 78;
    tmp[33] = 0;
    tmp[34] &= 0xfcU;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
    memcpy(tmp, sig, sizeof sig);
    tmp[2336U + 80U] = 81;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
    memcpy(tmp, sig, sizeof sig);
    tmp[2336U + 1U] = tmp[2336U];
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
    memcpy(tmp, sig, sizeof sig);
    tmp[2336U + 80U] = 2;
    tmp[2336U + 81U] = 1;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
    memcpy(tmp, sig, sizeof sig);
    tmp[2336U + 79U] = 1;
    bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
    memcpy(key, pk, sizeof pk);
    key[0] ^= 1U;
    bad(key, sizeof key, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);

    for (unsigned i = 0; i < 100U; i++) {
        for (unsigned j = 0; j < sizeof sig; j++)
            tmp[j] = (uint8_t)rand32();
        bad(pk, sizeof pk, msg, sizeof msg, ctx, sizeof ctx, tmp, sizeof sig);
        for (unsigned j = 0; j < sizeof pk; j++)
            key[j] = (uint8_t)rand32();
        bad(key, sizeof key, msg, sizeof msg, ctx, sizeof ctx, sig, sizeof sig);
    }

    sk[128] = (uint8_t)((sk[128] & 0xf8U) | 7U);
    if (mldsa44_sign(tmp, sk, sizeof sk, msg, sizeof msg,
                     ctx, sizeof ctx, rnd) == 0)
        abort();
    puts("negative verification and secret decode passed");
    printf("negative cases: %u\n", cases);
    return EXIT_SUCCESS;
}
