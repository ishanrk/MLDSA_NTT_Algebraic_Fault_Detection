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

enum {
    MLDSA44_SHA2_256 = 1,
    MLDSA44_SHA2_384 = 2,
    MLDSA44_SHA2_512 = 3,
    MLDSA44_SHA2_224 = 4,
    MLDSA44_SHA2_512_224 = 5,
    MLDSA44_SHA2_512_256 = 6,
    MLDSA44_SHA3_224 = 7,
    MLDSA44_SHA3_256 = 8,
    MLDSA44_SHA3_384 = 9,
    MLDSA44_SHA3_512 = 10,
    MLDSA44_SHAKE128 = 11,
    MLDSA44_SHAKE256 = 12
};

int mldsa44_keygen(uint8_t pk[MLDSA44_PUBLICKEY_BYTES],
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

int mldsa44_sign_digest(uint8_t sig[MLDSA44_SIGNATURE_BYTES],
                        const uint8_t *sk, size_t sklen,
                        unsigned hash, const uint8_t *digest, size_t dlen,
                        const uint8_t *ctx, size_t clen,
                        const uint8_t rnd[MLDSA44_RANDOM_BYTES]);

int mldsa44_verify_digest(const uint8_t *pk, size_t pklen,
                          unsigned hash, const uint8_t *digest, size_t dlen,
                          const uint8_t *ctx, size_t clen,
                          const uint8_t *sig, size_t siglen);

#endif
