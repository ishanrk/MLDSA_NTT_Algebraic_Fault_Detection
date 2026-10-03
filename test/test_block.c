#include "block_guard.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static uint32_t state = 1;

static uint32_t next_value(void)
{
    state ^= state << 13;
    state ^= state >> 17;
    state ^= state << 5;
    return state % MLDSA_Q;
}

int main(void)
{
    mldsa_poly a;
    mldsa_ntt ordinary, checked;
    for (unsigned trial = 0; trial < 512; trial++)
    {
        for (unsigned i = 0; i < MLDSA_N; i++)
        {
            a.c[i] = trial < MLDSA_N ? (uint32_t)(i == trial) : next_value();
        }
        mldsa_ntt_forward(&ordinary, &a);
        assert(mldsa_ntt_forward_block(&checked, &a) == 0);
        assert(memcmp(&ordinary, &checked, sizeof checked) == 0);
    }
    puts("block checker: 512 clean transforms match");
    return 0;
}

