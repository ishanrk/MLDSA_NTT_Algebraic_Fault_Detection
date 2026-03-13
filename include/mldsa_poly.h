#ifndef MLDSA_POLY_H
#define MLDSA_POLY_H

#include <stdint.h>

enum { MLDSA_N = 256, MLDSA_Q = 8380417 };

typedef struct { uint32_t c[MLDSA_N]; } mldsa_poly;
typedef struct { uint32_t c[MLDSA_N]; } mldsa_ntt;

uint32_t mldsa_reduce(uint64_t a);
uint32_t mldsa_add(uint32_t a, uint32_t b);
uint32_t mldsa_sub(uint32_t a, uint32_t b);
uint32_t mldsa_mul(uint32_t a, uint32_t b);
int32_t mldsa_center(uint32_t a);
uint32_t mldsa_uncenter(int32_t a);

void mldsa_poly_add(mldsa_poly *r, const mldsa_poly *a, const mldsa_poly *b);
void mldsa_poly_sub(mldsa_poly *r, const mldsa_poly *a, const mldsa_poly *b);
void mldsa_ntt_forward(mldsa_ntt *r, const mldsa_poly *a);
void mldsa_ntt_inverse(mldsa_poly *r, const mldsa_ntt *a);
void mldsa_ntt_mul(mldsa_ntt *r, const mldsa_ntt *a, const mldsa_ntt *b);
void mldsa_poly_mul(mldsa_poly *r, const mldsa_poly *a, const mldsa_poly *b);

#endif
