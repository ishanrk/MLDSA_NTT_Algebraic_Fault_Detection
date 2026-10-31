#include "mldsa44.h"
#include "mldsa_poly.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef __APPLE__
#include <sys/random.h>
#endif

static unsigned calls, faulted, twiddles;
static int mode, active;

int mldsa_encoded_random(uint8_t *out, size_t len)
{
#ifdef __APPLE__
    arc4random_buf(out, len);
    return 0;
#else
    while (len) {
        ssize_t n = getrandom(out, len, 0);
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0)
            return -1;
        out += n;
        len -= (size_t)n;
    }
    return 0;
#endif
}

void mldsa_demo_ntt_begin(void)
{
    calls++;
    // Signing performs twelve secret NTTs, then four nonce NTTs, then c.
    active = (mode == 1 && calls >= 13U && calls <= 16U) ||
             (mode == 2 && calls == 17U);
    if (active)
        faulted++;
}

uint32_t mldsa_demo_ntt_twiddle(uint32_t z)
{
    if (active) {
        twiddles++;
        return 0;
    }
    return z;
}

static void die(const char *s)
{
    fprintf(stderr, "%s\n", s);
    exit(2);
}

static void read_exact(const char *path, uint8_t *dst, size_t len)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        die("cannot open input");
    if (fread(dst, 1, len, f) != len || fgetc(f) != EOF)
        die("wrong input length");
    if (fclose(f))
        die("cannot close input");
}

static size_t read_message(const char *path, uint8_t *dst, size_t cap)
{
    FILE *f = fopen(path, "rb");
    size_t len;
    if (!f)
        die("cannot open message");
    len = fread(dst, 1, cap, f);
    if (ferror(f) || !feof(f))
        die("message too long");
    if (fclose(f))
        die("cannot close message");
    return len;
}

static void write_exact(const char *path, const uint8_t *src, size_t len)
{
    FILE *f = fopen(path, "wb");
    if (!f)
        die("cannot create output");
    if (fwrite(src, 1, len, f) != len || fclose(f))
        die("cannot write output");
}

int main(int argc, char **argv)
{
    uint8_t pk[MLDSA44_PUBLICKEY_BYTES], sk[MLDSA44_SECRETKEY_BYTES];
    uint8_t sig[MLDSA44_SIGNATURE_BYTES], seed[32], msg[4096];
    size_t mlen;
    int rc;
    if (argc == 5 && !strcmp(argv[1], "keygen")) {
        read_exact(argv[4], seed, sizeof seed);
        if (mldsa44_keygen(pk, sk, seed))
            die("keygen failed");
        write_exact(argv[2], pk, sizeof pk);
        write_exact(argv[3], sk, sizeof sk);
        puts("KEYGEN_OK");
        return 0;
    }
    if (argc == 5 && !strcmp(argv[1], "verify")) {
        read_exact(argv[2], pk, sizeof pk);
        mlen = read_message(argv[3], msg, sizeof msg);
        read_exact(argv[4], sig, sizeof sig);
        rc = mldsa44_verify(pk, sizeof pk, msg, mlen, NULL, 0, sig, sizeof sig);
        puts(rc ? "VERIFY_FAIL" : "VERIFY_OK");
        return rc ? 1 : 0;
    }
    if (argc != 7 || strcmp(argv[1], "sign"))
        die("usage: demo keygen pk sk seed | verify pk msg sig | sign sk msg sig rnd none|nonce|challenge");
    read_exact(argv[2], sk, sizeof sk);
    mlen = read_message(argv[3], msg, sizeof msg);
    read_exact(argv[5], seed, sizeof seed);
    if (!strcmp(argv[6], "none")) mode = 0;
    else if (!strcmp(argv[6], "nonce")) mode = 1;
    else if (!strcmp(argv[6], "challenge")) mode = 2;
    else die("unknown fault mode");
    memset(sig, 0xa5, sizeof sig);
    rc = mldsa44_sign(sig, sk, sizeof sk, msg, mlen, NULL, 0, seed);
    fprintf(stderr, "forward_ntts=%u faulted_ntts=%u zero_twiddles=%u\n",
            calls, faulted, twiddles);
    if (rc) {
        for (size_t i = 0; i < sizeof sig; i++)
            if (sig[i] != 0xa5)
                die("signing failed after writing signature bytes");
        puts("SIGN_ABORT");
        return 4;
    }
    if (mode && calls > 17U) {
        puts("FAULTED_ATTEMPT_REJECTED");
        return 5;
    }
    if (mode && faulted == 0)
        die("fault hook never activated");
    write_exact(argv[4], sig, sizeof sig);
    puts("SIGN_RELEASED");
    return 0;
}
