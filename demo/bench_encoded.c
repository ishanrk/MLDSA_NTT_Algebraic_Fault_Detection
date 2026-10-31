#define _POSIX_C_SOURCE 200809L
#include "mldsa_checker.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#ifndef __APPLE__
#include <sys/random.h>
#endif
#include <time.h>

int mldsa_encoded_random(uint8_t *out, size_t len)
{
#ifdef __APPLE__
    arc4random_buf(out, len);
    return 0;
#else
    while (len) {
        ssize_t n = getrandom(out, len, 0);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        out += n;
        len -= (size_t)n;
    }
    return 0;
#endif
}

static uint64_t now(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
    return (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
}

static uint64_t median(uint64_t x[5])
{
    for (unsigned i = 1; i < 5; i++) {
        uint64_t v = x[i];
        unsigned j = i;
        while (j && x[j - 1] > v) { x[j] = x[j - 1]; j--; }
        x[j] = v;
    }
    return x[2];
}

int main(void)
{
    mldsa_poly a;
    mldsa_ntt base, checked;
    mldsa_poly batch[4];
    mldsa_ntt result[4];
    uint64_t simple[5], encoded[5], simple4[5], encoded4[5];
    volatile uint32_t sink = 0;
    for (unsigned i = 0; i < MLDSA_N; i++) a.c[i] = (i * 12345U) % MLDSA_Q;
    for (unsigned i = 0; i < 4; i++) batch[i] = a;
    mldsa_ntt_forward(&base, &a);
    if (mldsa_ntt_forward_encoded(&checked, &a)) return 2;
    for (unsigned i = 0; i < MLDSA_N; i++)
        if (base.c[i] != checked.c[i]) return 3;
    for (unsigned pass = 0; pass < 5; pass++) {
        uint64_t t = now();
        for (unsigned i = 0; i < 2000; i++) {
            mldsa_ntt_forward(&base, &a);
            sink ^= base.c[i % MLDSA_N];
        }
        simple[pass] = now() - t;
        t = now();
        for (unsigned i = 0; i < 2000; i++) {
            if (mldsa_ntt_forward_encoded(&checked, &a)) return 4;
            sink ^= checked.c[i % MLDSA_N];
        }
        encoded[pass] = now() - t;
        t = now();
        for (unsigned i = 0; i < 2000; i++) {
            for (unsigned j = 0; j < 4; j++)
                mldsa_ntt_forward(&result[j], &batch[j]);
            sink ^= result[0].c[i % MLDSA_N];
        }
        simple4[pass] = now() - t;
        t = now();
        for (unsigned i = 0; i < 2000; i++) {
            if (mldsa_ntt_forward_encoded4(result, batch)) return 5;
            sink ^= result[0].c[i % MLDSA_N];
        }
        encoded4[pass] = now() - t;
    }
    uint64_t a_ns = median(simple) / 2000;
    uint64_t b_ns = median(encoded) / 2000;
    printf("host baseline ns/NTT: %llu\n", (unsigned long long)a_ns);
    printf("host encoded ns/NTT: %llu\n", (unsigned long long)b_ns);
    printf("host added cost: %.1f%% (including getrandom)\n",
           100.0 * ((double)b_ns / (double)a_ns - 1.0));
    a_ns = median(simple4) / 8000;
    b_ns = median(encoded4) / 8000;
    printf("host four input baseline ns/NTT: %llu\n", (unsigned long long)a_ns);
    printf("host four input encoded ns/NTT: %llu\n", (unsigned long long)b_ns);
    printf("host four input added cost: %.1f%% (including getrandom)\n",
           100.0 * ((double)b_ns / (double)a_ns - 1.0));
    printf("same mathematical output: yes; sink: %u\n", (unsigned)sink);
    return 0;
}
