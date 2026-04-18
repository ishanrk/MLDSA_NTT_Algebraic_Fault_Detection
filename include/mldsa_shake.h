#ifndef MLDSA_SHAKE_H
#define MLDSA_SHAKE_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint64_t a[25];
    size_t rate;
    size_t pos;
    int squeezing;
} mldsa_shake;

void mldsa_shake_init(mldsa_shake *s, unsigned strength);
void mldsa_shake_absorb(mldsa_shake *s, const uint8_t *in, size_t n);
void mldsa_shake_squeeze(mldsa_shake *s, uint8_t *out, size_t n);
void mldsa_shake128(uint8_t *out, size_t outlen, const uint8_t *in, size_t inlen);
void mldsa_shake256(uint8_t *out, size_t outlen, const uint8_t *in, size_t inlen);

#endif
