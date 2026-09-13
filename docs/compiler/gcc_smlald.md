# GCC SMLALD patch

I wrote this [GCC patch](gcc-smlald.patch) while investigating ARM instruction counts.

The patch adds two ARM peephole patterns for ordinary C that computes two packed signed halfword products and accumulates them into a `64` bit value. The patterns cover the two instruction orders emitted after register allocation. They require little endian integer SIMD support, matching packed inputs, dead extraction temporaries and valid register overlaps.

```c
typedef short v2hi __attribute__((vector_size(4)));

long long foo(v2hi a, v2hi b, long long acc)
{
    return acc + (long long)a[0] * b[0] + (long long)a[1] * b[1];
}
```

For the recorded Cortex M4 `-O2 -mthumb` example:

```asm
sbfx    ip, r0, #16, #16
smlalbb r2, r3, r0, r1
sbfx    r1, r1, #16, #16
smlalbb r2, r3, ip, r1
```

becomes

```asm
smlald  r2, r3, r0, r1
```

The recorded compiler experiment reduced the arithmetic sequence from `4` instructions to `1` and the complete function from `7` to `4`. The supplied validation report records matching three stage native bootstrap and full test outcomes against the unpatched parent, with no recorded regressions. ARM compile checks reported `4 PASS` for the new tests, `38 PASS` and `2 XFAIL` for the focused selection, and identical outcomes across `636` existing compile tests. These are the supplied compiler experiment results; this repository does not rerun the GCC bootstrap or claim ARM execution coverage for the patch.

Status: development patch. A public GCC archive reference has not been verified. The linked text preserves the supplied patch; it is not evidence of upstream acceptance.

The ML-DSA benchmark uses the toolchain recorded in [the raw measurements](../../bench/qemu_benchmark.json), with canonical `32` bit field coefficients. It does not use this packed `16` bit optimization. Any application to the cryptographic code would require separate implementation and measurement.
