#ifndef MLDSA44_INTERNAL_H
#define MLDSA44_INTERNAL_H

#include "mldsa_poly.h"

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
    MLDSA44_ALPHA = 190464
};

void mldsa44_power2round(uint32_t r, uint32_t *hi, int32_t *lo);
void mldsa44_decompose(uint32_t r, uint32_t *hi, int32_t *lo);
uint32_t mldsa44_highbits(uint32_t r);
int32_t mldsa44_lowbits(uint32_t r);
uint8_t mldsa44_make_hint(uint32_t z, uint32_t r);
uint32_t mldsa44_use_hint(uint8_t h, uint32_t r);
int mldsa44_norm(const mldsa_poly *a, uint32_t bound);

#endif
