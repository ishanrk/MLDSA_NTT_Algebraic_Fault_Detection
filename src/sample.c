#include "mldsa44_internal.h"
#include "mldsa_shake.h"

#include <string.h>

static void sample_ntt(mldsa_ntt *a, const uint8_t seed[34])
{
    mldsa_shake s;
    unsigned j = 0;

    mldsa_shake_init(&s, 128);
    mldsa_shake_absorb(&s, seed, 34);
    while (j < MLDSA_N) {
        uint8_t b[3];
        uint32_t x;
        mldsa_shake_squeeze(&s, b, 3);
        x = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | (((uint32_t)b[2] & 127U) << 16);
        if (x < MLDSA_Q)
            a->c[j++] = x;
    }
}

static void sample_eta(mldsa_poly *a, const uint8_t seed[66])
{
    mldsa_shake s;
    unsigned j = 0;

    mldsa_shake_init(&s, 256);
    mldsa_shake_absorb(&s, seed, 66);
    while (j < MLDSA_N) {
        uint8_t b;
        mldsa_shake_squeeze(&s, &b, 1);
        for (unsigned k = 0; k < 2 && j < MLDSA_N; k++) {
            unsigned x = k == 0U ? b & 15U : b >> 4;
            if (x < 15U)
                a->c[j++] = mldsa_uncenter(2 - (int32_t)(x % 5U));
        }
    }
}

void mldsa44_expand_a(mldsa_ntt a[4][4], const uint8_t rho[32])
{
    uint8_t seed[34];
    memcpy(seed, rho, 32);
    for (unsigned r = 0; r < 4; r++) {
        for (unsigned c = 0; c < 4; c++) {
            seed[32] = (uint8_t)c;
            seed[33] = (uint8_t)r;
            sample_ntt(&a[r][c], seed);
        }
    }
}

void mldsa44_expand_s(mldsa_poly s1[4], mldsa_poly s2[4], const uint8_t rho[64])
{
    uint8_t seed[66];
    memcpy(seed, rho, 64);
    for (unsigned i = 0; i < 8; i++) {
        seed[64] = (uint8_t)i;
        seed[65] = 0;
        sample_eta(i < 4U ? &s1[i] : &s2[i - 4U], seed);
    }
}

void mldsa44_expand_mask(mldsa_poly y[4], const uint8_t rho[64], uint32_t nonce)
{
    uint8_t seed[66], buf[576];
    memcpy(seed, rho, 64);
    for (unsigned i = 0; i < 4; i++) {
        uint16_t n = (uint16_t)(nonce + i);
        seed[64] = (uint8_t)n;
        seed[65] = (uint8_t)(n >> 8);
        mldsa_shake256(buf, sizeof buf, seed, sizeof seed);
        (void)mldsa44_unpack_bits(&y[i], buf, 18, MLDSA44_GAMMA1, 262143U, 1);
    }
}

void mldsa44_sample_ball(mldsa_poly *c, const uint8_t seed[32])
{
    mldsa_shake s;
    uint8_t signs[8];

    memset(c, 0, sizeof *c);
    mldsa_shake_init(&s, 256);
    mldsa_shake_absorb(&s, seed, 32);
    mldsa_shake_squeeze(&s, signs, sizeof signs);
    for (unsigned i = MLDSA_N - MLDSA44_TAU; i < MLDSA_N; i++) {
        uint8_t j;
        do {
            mldsa_shake_squeeze(&s, &j, 1);
        } while (j > i);
        c->c[i] = c->c[j];
        c->c[j] = (signs[(i + MLDSA44_TAU - MLDSA_N) / 8U] >>
                   ((i + MLDSA44_TAU - MLDSA_N) % 8U)) & 1U ? MLDSA_Q - 1U : 1U;
    }
}
