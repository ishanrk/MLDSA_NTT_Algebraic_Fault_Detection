#include "mldsa_poly.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

static uint64_t seed;
static uint64_t state;

static uint64_t rand64(void)
{
    uint64_t z = (state += UINT64_C(0x9e3779b97f4a7c15));
    z = (z ^ (z >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94d049bb133111eb);
    return z ^ (z >> 31);
}

static void fail(const char *label, unsigned pos, unsigned i, uint32_t got, uint32_t want)
{
    fprintf(stderr, "%s seed=%" PRIu64 " pair=%u coefficient=%u got=%" PRIu32
            " want=%" PRIu32 "\n", label, seed, pos, i, got, want);
    exit(EXIT_FAILURE);
}

static void equal(const mldsa_poly *a, const mldsa_poly *b,
                  const char *label, unsigned pos)
{
    for (unsigned i = 0; i < MLDSA_N; i++)
        if (a->c[i] != b->c[i])
            fail(label, pos, i, a->c[i], b->c[i]);
}

static void schoolbook(mldsa_poly *r, const mldsa_poly *a, const mldsa_poly *b)
{
    int64_t c[MLDSA_N] = {0};

    for (unsigned i = 0; i < MLDSA_N; i++) {
        for (unsigned j = 0; j < MLDSA_N; j++) {
            int64_t t = (int64_t)a->c[i] * b->c[j];
            if (i + j < MLDSA_N)
                c[i + j] += t;
            else
                c[i + j - MLDSA_N] -= t;
        }
    }

    for (unsigned i = 0; i < MLDSA_N; i++) {
        int64_t t = c[i] % MLDSA_Q;
        if (t < 0)
            t += MLDSA_Q;
        r->c[i] = (uint32_t)t;
    }
}

static void check_pair(const mldsa_poly *a, const mldsa_poly *b,
                       const char *label, unsigned pos)
{
    mldsa_ntt x, y, z;
    mldsa_poly c, d, e;

    mldsa_ntt_forward(&x, a);
    mldsa_ntt_inverse(&c, &x);
    equal(&c, a, label, pos);

    mldsa_ntt_forward(&y, b);
    mldsa_ntt_inverse(&c, &y);
    equal(&c, b, label, pos);

    mldsa_ntt_mul(&z, &x, &y);
    mldsa_ntt_inverse(&c, &z);
    schoolbook(&d, a, b);
    equal(&c, &d, label, pos);

    mldsa_poly_mul(&e, a, b);
    equal(&e, &d, label, pos);

    mldsa_poly_add(&c, a, b);
    mldsa_poly_sub(&e, &c, b);
    equal(&e, a, label, pos);
}

static void check_arithmetic(void)
{
    uint32_t v[] = {0U, 1U, 2U, 4190208U, 4190209U,
                    MLDSA_Q - 2U, MLDSA_Q - 1U};

    for (unsigned i = 0; i < sizeof v / sizeof v[0]; i++) {
        uint32_t a = v[i];
        int32_t c = mldsa_center(a);
        if (mldsa_uncenter(c) != a)
            fail("center", 0, i, mldsa_uncenter(c), a);
        for (unsigned j = 0; j < sizeof v / sizeof v[0]; j++) {
            uint32_t b = v[j];
            uint32_t sum = (uint32_t)(((uint64_t)a + b) % MLDSA_Q);
            uint32_t prod = (uint32_t)(((uint64_t)a * b) % MLDSA_Q);
            uint32_t diff = (uint32_t)(((uint64_t)a + MLDSA_Q - b) % MLDSA_Q);
            if (mldsa_add(a, b) != sum)
                fail("add", i, j, mldsa_add(a, b), sum);
            if (mldsa_sub(a, b) != diff)
                fail("sub", i, j, mldsa_sub(a, b), diff);
            if (mldsa_mul(a, b) != prod)
                fail("mul", i, j, mldsa_mul(a, b), prod);
        }
    }
    if (mldsa_reduce(UINT64_MAX) != (uint32_t)(UINT64_MAX % MLDSA_Q))
        fail("reduce", 0, 0, mldsa_reduce(UINT64_MAX),
             (uint32_t)(UINT64_MAX % MLDSA_Q));
}

static void check_edges(void)
{
    mldsa_poly a = {{0}}, b = {{0}};

    check_pair(&a, &b, "zero", 0);

    for (unsigned i = 0; i < MLDSA_N; i++) {
        a.c[i] = 1;
        b.c[i] = MLDSA_Q - 1U;
    }
    check_pair(&a, &a, "ones", 0);
    check_pair(&b, &b, "minus ones", 0);
    check_pair(&a, &b, "opposites", 0);

    for (unsigned i = 0; i < MLDSA_N; i++) {
        a.c[i] = (i & 1U) ? MLDSA_Q - 1U : 0U;
        b.c[i] = (i & 1U) ? 0U : MLDSA_Q - 1U;
    }
    check_pair(&a, &b, "alternating", 0);

    for (unsigned i = 0; i < MLDSA_N; i++) {
        a.c[i] = (uint32_t)(i % 6U == 0U ? 0U :
                   i % 6U == 1U ? 1U :
                   i % 6U == 2U ? MLDSA_Q - 1U :
                   i % 6U == 3U ? MLDSA_Q - 2U :
                   i % 6U == 4U ? 4190208U : 4190209U);
        b.c[i] = a.c[MLDSA_N - 1U - i];
    }
    check_pair(&a, &b, "boundaries", 0);

    for (unsigned i = 0; i < MLDSA_N; i++) {
        mldsa_poly x = {{0}}, y = {{0}};
        mldsa_poly got, want = {{0}};
        x.c[i] = 1;
        y.c[MLDSA_N - 1U] = 1;
        check_pair(&x, &y, "monomial wrap", i);
        mldsa_poly_mul(&got, &x, &y);
        want.c[i == 0U ? MLDSA_N - 1U : i - 1U] =
            i == 0U ? 1U : MLDSA_Q - 1U;
        equal(&got, &want, "monomial direct", i);
        x.c[i] = MLDSA_Q - 1U;
        check_pair(&x, &y, "negative monomial", i);
        mldsa_poly_mul(&got, &x, &y);
        want.c[i == 0U ? MLDSA_N - 1U : i - 1U] =
            i == 0U ? MLDSA_Q - 1U : 1U;
        equal(&got, &want, "negative direct", i);
    }
}

static void check_random(void)
{
    for (unsigned pos = 0; pos < 10000U; pos++) {
        mldsa_poly a, b;
        for (unsigned i = 0; i < MLDSA_N; i++) {
            a.c[i] = (uint32_t)(rand64() % MLDSA_Q);
            b.c[i] = (uint32_t)(rand64() % MLDSA_Q);
        }
        check_pair(&a, &b, "random", pos);
    }
}

int main(int argc, char **argv)
{
    const char *s = argc > 1 ? argv[1] : getenv("MLDSA_TEST_SEED");
    char *end;

    if (argc > 2) {
        fprintf(stderr, "usage: %s [seed]\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (s == NULL)
        s = "132164";
    errno = 0;
    seed = strtoull(s, &end, 0);
    if (errno != 0 || *s == '\0' || *end != '\0') {
        fprintf(stderr, "invalid seed: %s\n", s);
        return EXIT_FAILURE;
    }
    state = seed;

    check_arithmetic();
    check_edges();
    check_random();
    printf("passed: seed=%" PRIu64 " random pairs=10000\n", seed);
    return EXIT_SUCCESS;
}
