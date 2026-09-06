# Thesis results from repository evidence

Generated from [bench/thesis.json](../bench/thesis.json) by `python3 tools/render_thesis.py`. Numbers are read from the raw dataset.

Available regression: **passed**, 97 stages, 177.555 seconds wall time. Physical status: **pending**. Regression and proof wall times are host reproduction times, not performance measurements.

Run started `2026-10-03T15:51:59.190837+00:00`; source base `861fe053098145543b924907cf0f1ef9e03bb788`. Source digests identify the tested tree, including uncommitted artifact tooling at collection.

The physical milestone is incomplete while cycles, stack and physical correctness tests are pending. Linked flash is ELF text + data; static RAM is ELF data + BSS. Reference builds do not identify the attached board. Baseline physical overhead also stays pending until measured.

## Baseline: physical cycle statistics

| Operation | Samples | Min | Median | Max | P95 |
| --- | --- | --- | --- | --- | --- |
| ntt_forward | pending | pending | pending | pending | pending |
| ntt_inverse | pending | pending | pending | pending | pending |
| pointwise | pending | pending | pending | pending | pending |
| keygen | pending | pending | pending | pending | pending |
| sign | pending | pending | pending | pending | pending |
| verify | pending | pending | pending | pending | pending |

## Abdelmonem two checks: physical cycle statistics

| Operation | Samples | Min | Median | Max | P95 |
| --- | --- | --- | --- | --- | --- |
| ntt_forward | pending | pending | pending | pending | pending |
| ntt_inverse | pending | pending | pending | pending | pending |
| pointwise | pending | pending | pending | pending | pending |
| keygen | pending | pending | pending | pending | pending |
| sign | pending | pending | pending | pending | pending |
| verify | pending | pending | pending | pending | pending |

## Our deterministic two checks: physical cycle statistics

| Operation | Samples | Min | Median | Max | P95 |
| --- | --- | --- | --- | --- | --- |
| ntt_forward | pending | pending | pending | pending | pending |
| ntt_inverse | pending | pending | pending | pending | pending |
| pointwise | pending | pending | pending | pending | pending |
| keygen | pending | pending | pending | pending | pending |
| sign | pending | pending | pending | pending | pending |
| verify | pending | pending | pending | pending | pending |

## Physical cycle overhead relative to baseline median

| Variant | Operation | Overhead (percent) |
| --- | --- | --- |
| Baseline | ntt_forward | pending |
| Baseline | ntt_inverse | pending |
| Baseline | pointwise | pending |
| Baseline | keygen | pending |
| Baseline | sign | pending |
| Baseline | verify | pending |
| Abdelmonem two checks | ntt_forward | pending |
| Abdelmonem two checks | ntt_inverse | pending |
| Abdelmonem two checks | pointwise | pending |
| Abdelmonem two checks | keygen | pending |
| Abdelmonem two checks | sign | pending |
| Abdelmonem two checks | verify | pending |
| Our deterministic two checks | ntt_forward | pending |
| Our deterministic two checks | ntt_inverse | pending |
| Our deterministic two checks | pointwise | pending |
| Our deterministic two checks | keygen | pending |
| Our deterministic two checks | sign | pending |
| Our deterministic two checks | verify | pending |

## Reference target linked memory and physical stack high water (bytes)

| Target | Variant | Linked flash | Static RAM | Keygen stack | Sign stack | Verify stack |
| --- | --- | --- | --- | --- | --- | --- |
| NUCLEO-F411RE | Baseline | 12812 | 17096 | pending | pending | pending |
| NUCLEO-F411RE | Abdelmonem two checks | 15644 | 17096 | pending | pending | pending |
| NUCLEO-F411RE | Our deterministic two checks | 16136 | 17096 | pending | pending | pending |
| NUCLEO-F446RE | Baseline | 12812 | 17096 | pending | pending | pending |
| NUCLEO-F446RE | Abdelmonem two checks | 15644 | 17096 | pending | pending | pending |
| NUCLEO-F446RE | Our deterministic two checks | 16136 | 17096 | pending | pending | pending |

## Modular function calls per forward transform

| Variant | Total mul | Total add | Total sub | Extra mul | Extra add |
| --- | --- | --- | --- | --- | --- |
| Baseline | 1024 | 1024 | 1024 | 0 | 0 |
| Abdelmonem two checks | 1664 | 2048 | 1024 | 640 | 1024 |
| Our deterministic two checks | 1792 | 2048 | 1024 | 768 | 1024 |

## Scalar checks and generated coefficient storage

| Variant | Checks | Stored coefficients | Constant bytes |
| --- | --- | --- | --- |
| Baseline | 0 | 0 | 0 |
| Abdelmonem two checks | 2 | 640 | 2560 |
| Our deterministic two checks | 2 | 768 | 3072 |

## Exact modeled network and certificate parameters

| Variant | n | q | h | Locations | Pairs | k | K | D |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Abdelmonem two checks | 256 | 8380417 | 8 | 2304 | 2653056 | N/A | N/A | N/A |
| Our deterministic two checks | 256 | 8380417 | 8 | 2304 | 2653056 | 4 | 61 | 138653 |

## Exact certificate failure counts

| Variant | Zero first | Zero second | Duplicate ratios | Zero determinants |
| --- | --- | --- | --- | --- |
| Abdelmonem two checks | 0 | 0 | not separately recorded | 0 |
| Our deterministic two checks | 0 | 0 | 0 | 0 |

## Exact certificate row and propagation identities

| Variant | Row identities | Unit propagation | Intermediate identity |
| --- | --- | --- | --- |
| Abdelmonem two checks | direct evaluation and network pullback passed | all unit wires matched the production network | N/A |
| Our deterministic two checks | direct evaluation and network pullback passed | all unit wires matched the production network | every intermediate vector propagated to its unit wire output |

## Focused CBMC properties: arithmetic

| Property | Unwind | Unwinding checks | Result | Seconds |
| --- | --- | --- | --- | --- |
| reduce | 1 | enabled; passed | passed | 0.469 |
| add | 1 | enabled; passed | passed | 0.059 |
| sub | 1 | enabled; passed | passed | 0.117 |
| mul | 1 | enabled; passed | passed | 1.068 |
| center | 1 | enabled; passed | passed | 0.058 |
| uncenter | 1 | enabled; passed | passed | 0.069 |
| forward_butterfly | 1 | enabled; passed | passed | 4.943 |
| inverse_butterfly | 1 | enabled; passed | passed | 4.083 |
| forward_layer_0 | 257 | enabled; passed | passed | 1.693 |
| forward_layer_1 | 257 | enabled; passed | passed | 1.975 |
| forward_layer_2 | 257 | enabled; passed | passed | 2.135 |
| forward_layer_3 | 257 | enabled; passed | passed | 1.85 |
| forward_layer_4 | 257 | enabled; passed | passed | 1.811 |
| forward_layer_5 | 257 | enabled; passed | passed | 1.794 |
| forward_layer_6 | 257 | enabled; passed | passed | 1.823 |
| forward_layer_7 | 257 | enabled; passed | passed | 1.764 |
| forward_memory | 257 | enabled; passed | passed | 18.872 |
| inverse_memory | 257 | enabled; passed | passed | 22.354 |
| pointwise_memory | 257 | enabled; passed | passed | 1.221 |

## Focused CBMC properties: checkers

| Property | Unwind | Unwinding checks | Result | Seconds |
| --- | --- | --- | --- | --- |
| prior_base | 1 | enabled; passed | passed | 0.032 |
| prior_input_step | 1 | enabled; passed | passed | 0.162 |
| prior_output_step | 1 | enabled; passed | passed | 0.171 |
| prior_decide | 1 | enabled; passed | passed | 0.062 |
| our_base | 1 | enabled; passed | passed | 0.03 |
| our_input_step | 1 | enabled; passed | passed | 0.151 |
| our_output_step | 1 | enabled; passed | passed | 0.23 |
| our_decide | 1 | enabled; passed | passed | 0.062 |
| prior_memory | 257 | enabled; passed | passed | 10.807 |
| our_memory | 257 | enabled; passed | passed | 11.754 |

## Focused portable C verification summary

| Group | CBMC | Solver | Jobs | Seconds | Result |
| --- | --- | --- | --- | --- | --- |
| arithmetic | 6.10.0 (cbmc-6.10.0) | Z3 version 4.8.12 - 64 bit | 19 | 68.158 | passed |
| checkers | 6.10.0 (cbmc-6.10.0) | Z3 version 4.8.12 - 64 bit | 10 | 23.461 | passed |

## Final comprehensive host regression

| Mode | Polynomial seed | Random pairs | Baseline negatives | Prior negatives | Our negatives | Result |
| --- | --- | --- | --- | --- | --- | --- |
| gcc | 132164 | 10000 | 479 | 479 | 479 | passed |
| clang | 132164 | 10000 | 479 | 479 | 479 | passed |
| asan | 132164 | 10000 | 479 | 479 | 479 | passed |
| ubsan | 132164 | 10000 | 479 | 479 | 479 | passed |

## All supported official vectors per applicable variant and build mode

| Dataset / interface | Cases |
| --- | --- |
| SHAKE-128-FIPS202 | 269 |
| SHAKE-256-FIPS202 | 41 |
| ML-DSA-keyGen-FIPS204 | 25 |
| ML-DSA-sigGen-FIPS204/pure | 30 |
| ML-DSA-sigGen-FIPS204/preHash | 30 |
| ML-DSA-sigVer-FIPS204/pure | 15 |
| ML-DSA-sigVer-FIPS204/preHash | 15 |

## Certificate coefficient digests

Abdelmonem two checks: `9281c37271baa76755a5873797b948142bc3ae8c45865df69326589a892a58df`.

Our deterministic two checks: `dc167f43461e2c9c079bb79ded94a5b6a3af39062ea1de36b64f71ce01f9b2ec`.

The prior generator verifies distinct normalized ratios internally and enumerates every determinant, but does not store a separate duplicate-ratio counter; the table preserves that distinction. Both certificates have zero recorded failures.

These are exact checks of concrete finite-field coefficient conditions. They do not formally verify the generator or prove the general construction theorem. CBMC verifies portable C components under the [documented contracts and assumptions](verification.md), with inspected composition rather than an automatically checked global ML DSA or NTT refinement.

The NIST scope is ML DSA 44 external pure and prehash interfaces; byte-aligned SHAKE; other parameter sets, internal interfaces and bit-oriented SHAKE are unsupported. Keygen, pure signing, verification and prehash vectors run for all three variants in each of the four host modes. SHAKE, arithmetic and sampling use shared baseline code; protected compact tests check checksum behavior. The existing 10000-pair test executes once per compiler/sanitizer mode with the recorded seed. The existing 200-case pqcrypto differential suite executes once per variant with GCC.

Threat model: at most two additive deviations at modeled forward NTT boundary wires over the finite field, with trusted checker arithmetic, weights and control flow. Physical Cortex M4 cycle/stack observations, when collected, establish cost on those inputs; they do not establish resistance against every physical fault mechanism.

Individual LaTeX fragments are in [bench/thesis](../bench/thesis); `bench/thesis/tables.tex` includes every table. Wrap or resize wide tables in the thesis layout. No additional LaTeX package is required by the generated fragments.

Manual thesis work: integrate the theorem proof and its assumptions; position the result against related work; explain the cost/construction tradeoff; add board observations and physical-method discussion after capture; write the conclusions and institutional formatting.
