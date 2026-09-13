# Checker research comparison

Generated from [raw results](../bench/comparison.json) by `python3 tools/render_comparison.py`. Rebuild all evidence with `make comparison`.

## Forward NTT operations

| Variant | Checks | Stored coefficients | Total field mul | Total field add | Extra field mul | Extra field add |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline | 0 | 0 | 1024 | 1024 | 0 | 0 |
| Abdelmonem et al. | 2 | 640 | 1664 | 2048 | 640 | 1024 |
| Current method | 2 | 768 | 1792 | 2048 | 768 | 1024 |

## ARM emulator image sizes (bytes)

| Variant | Constant tables | ARM text | ARM data | ARM BSS |
| --- | --- | --- | --- | --- |
| Baseline | 0 | 11248 | 0 | 14876 |
| Abdelmonem et al. | 2560 | 14080 | 0 | 14876 |
| Current method | 3072 | 14576 | 0 | 14876 |

## Implementation evidence

| Variant | Exact certificate | Pairs | Certificate failures | CBMC jobs passed | QEMU correctness |
| --- | --- | --- | --- | --- | --- |
| Baseline | not applicable | N/A | N/A | 19 common + 0 checker | passed |
| Abdelmonem et al. | passed | 2653056 | 0 | 19 common + 5 checker | passed |
| Current method | passed | 2653056 | 0 | 19 common + 5 checker | passed |

## Physical measurements

| Variant | NTT cycles | Keygen cycles | Sign cycles | Verify cycles | Flash bytes | Static RAM bytes | Stack bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | pending | pending | pending | pending | pending | pending | pending |
| Abdelmonem et al. | pending | pending | pending | pending | pending | pending | pending |
| Current method | pending | pending | pending | pending | pending | pending | pending |

Counts are actual modular function calls for one fixed nonzero forward NTT input. Extra counts subtract baseline calls. Stored coefficients count generated uint32 table entries; implicit unity weights require no storage. Both defenses have two scalar equality checks, implemented as four checksum accumulations.

The current checker uses 128 more field multiplications and 512 more table bytes than the Abdelmonem et al. checker. Its improvement is the sufficient construction field bound; these results make no speedup claim.

ARM compiler: `arm-none-eabi-gcc (15:10.3-2021.07-4) 10.3.1 20210621 (release)`. Flags: `-mcpu=cortex-m4 -mthumb -mfloat-abi=soft -std=c11 -O2 -ffreestanding -fno-builtin -fdata-sections -ffunction-sections -Wall -Wextra -Wpedantic -Wconversion -Wshadow`. Linker: `platform/cortexm4/mps2.ld`. Text includes readonly tables and vectors. All variants use the same benchmark harness without injection hooks. These sizes describe the emulator layout, not measured Nucleo flash or RAM.

CBMC counts refer to [focused component proofs](verification.md), with shared arithmetic/layer/loop proofs counted once per applicable variant. There is no automatically checked global transform or ML DSA refinement. No fault acceptance uses compositional reasoning and exact row certificates. The general determinant theorem is not a CBMC result.

Both protected variants certify nonzero determinants for every distinct pair of modeled boundary wires, covering nonzero result errors caused by at most two additive wire deviations with trusted checker arithmetic, weights and control flow. Baseline has no such checker guarantee. Physical fault injection has not been evaluated. QEMU supplies correctness evidence only; physical cycles, overhead percentages, flash, RAM and stack measurements are pending.
