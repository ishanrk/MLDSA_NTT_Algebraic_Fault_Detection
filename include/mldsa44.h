#ifndef MLDSA44_H
#define MLDSA44_H

#include <stddef.h>
#include <stdint.h>

enum {
    MLDSA44_PUBLICKEY_BYTES = 1312,
    MLDSA44_SECRETKEY_BYTES = 2560,
    MLDSA44_SIGNATURE_BYTES = 2420,
    MLDSA44_SEED_BYTES = 32,
    MLDSA44_RANDOM_BYTES = 32
};

void mldsa44_keygen(uint8_t pk[MLDSA44_PUBLICKEY_BYTES],
                    uint8_t sk[MLDSA44_SECRETKEY_BYTES],
                    const uint8_t seed[MLDSA44_SEED_BYTES]);

int mldsa44_sign(uint8_t sig[MLDSA44_SIGNATURE_BYTES],
                 const uint8_t *sk, size_t sklen,
                 const uint8_t *msg, size_t mlen,
                 const uint8_t *ctx, size_t clen,
                 const uint8_t rnd[MLDSA44_RANDOM_BYTES]);

int mldsa44_verify(const uint8_t *pk, size_t pklen,
                   const uint8_t *msg, size_t mlen,
                   const uint8_t *ctx, size_t clen,
                   const uint8_t *sig, size_t siglen);

#endif
