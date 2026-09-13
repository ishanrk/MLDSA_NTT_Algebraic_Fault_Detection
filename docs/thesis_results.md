| Operation | Samples | Min | Median | Max | P95 |
| --- | --- | --- | --- | --- | --- |
| ntt_forward | pending | pending | pending | pending | pending |
| ntt_inverse | pending | pending | pending | pending | pending |
| pointwise | pending | pending | pending | pending | pending |
| keygen | pending | pending | pending | pending | pending |
| sign | pending | pending | pending | pending | pending |
| verify | pending | pending | pending | pending | pending |

| Operation | Samples | Min | Median | Max | P95 |
| --- | --- | --- | --- | --- | --- |
| ntt_forward | pending | pending | pending | pending | pending |
| ntt_inverse | pending | pending | pending | pending | pending |
| pointwise | pending | pending | pending | pending | pending |
| keygen | pending | pending | pending | pending | pending |
| sign | pending | pending | pending | pending | pending |
| verify | pending | pending | pending | pending | pending |

| Operation | Samples | Min | Median | Max | P95 |
| --- | --- | --- | --- | --- | --- |
| ntt_forward | pending | pending | pending | pending | pending |
| ntt_inverse | pending | pending | pending | pending | pending |
| pointwise | pending | pending | pending | pending | pending |
| keygen | pending | pending | pending | pending | pending |
| sign | pending | pending | pending | pending | pending |
| verify | pending | pending | pending | pending | pending |

| Variant | Operation | Overhead (percent) |
| --- | --- | --- |
| Baseline | ntt_forward | pending |
| Baseline | ntt_inverse | pending |
| Baseline | pointwise | pending |
| Baseline | keygen | pending |
| Baseline | sign | pending |
| Baseline | verify | pending |
| Abdelmonem et al. | ntt_forward | pending |
| Abdelmonem et al. | ntt_inverse | pending |
| Abdelmonem et al. | pointwise | pending |
| Abdelmonem et al. | keygen | pending |
| Abdelmonem et al. | sign | pending |
| Abdelmonem et al. | verify | pending |
| Current method | ntt_forward | pending |
| Current method | ntt_inverse | pending |
| Current method | pointwise | pending |
| Current method | keygen | pending |
| Current method | sign | pending |
| Current method | verify | pending |

| Target | Variant | Linked flash | Static RAM | Keygen stack | Sign stack | Verify stack |
| --- | --- | --- | --- | --- | --- | --- |
| `NUCLEO-F411RE` | Baseline | 12812 | 17096 | pending | pending | pending |
| `NUCLEO-F411RE` | Abdelmonem et al. | 15644 | 17096 | pending | pending | pending |
| `NUCLEO-F411RE` | Current method | 16136 | 17096 | pending | pending | pending |
| `NUCLEO-F446RE` | Baseline | 12812 | 17096 | pending | pending | pending |
| `NUCLEO-F446RE` | Abdelmonem et al. | 15644 | 17096 | pending | pending | pending |
| `NUCLEO-F446RE` | Current method | 16136 | 17096 | pending | pending | pending |

| Variant | Total mul | Total add | Total sub | Extra mul | Extra add |
| --- | --- | --- | --- | --- | --- |
| Baseline | 1024 | 1024 | 1024 | 0 | 0 |
| Abdelmonem et al. | 1664 | 2048 | 1024 | 640 | 1024 |
| Current method | 1792 | 2048 | 1024 | 768 | 1024 |

| Variant | Checks | Stored coefficients | Constant bytes |
| --- | --- | --- | --- |
| Baseline | 0 | 0 | 0 |
| Abdelmonem et al. | 2 | 640 | 2560 |
| Current method | 2 | 768 | 3072 |

| Variant | n | q | h | Locations | Pairs | k | K | D |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Abdelmonem et al. | 256 | 8380417 | 8 | 2304 | 2653056 | N/A | N/A | N/A |
| Current method | 256 | 8380417 | 8 | 2304 | 2653056 | 4 | 61 | 138653 |

| Variant | Zero first | Zero second | Duplicate ratios | Zero determinants |
| --- | --- | --- | --- | --- |
| Abdelmonem et al. | 0 | 0 | not separately recorded | 0 |
| Current method | 0 | 0 | 0 | 0 |

| Variant | Row identities | Unit propagation | Intermediate identity |
| --- | --- | --- | --- |
| Abdelmonem et al. | direct evaluation and network pullback passed | all unit wires matched the production network | N/A |
| Current method | direct evaluation and network pullback passed | all unit wires matched the production network | every intermediate vector propagated to its unit wire output |

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

| Group | CBMC | Solver | Jobs | Seconds | Result |
| --- | --- | --- | --- | --- | --- |
| arithmetic | 6.10.0 (cbmc-6.10.0) | Z3 version 4.8.12 - 64 bit | 19 | 68.158 | passed |
| checkers | 6.10.0 (cbmc-6.10.0) | Z3 version 4.8.12 - 64 bit | 10 | 23.461 | passed |

| Mode | Polynomial seed | Random pairs | Baseline negatives | Prior negatives | Current negatives | Result |
| --- | --- | --- | --- | --- | --- | --- |
| gcc | 132164 | 10000 | 479 | 479 | 479 | passed |
| clang | 132164 | 10000 | 479 | 479 | 479 | passed |
| asan | 132164 | 10000 | 479 | 479 | 479 | passed |
| ubsan | 132164 | 10000 | 479 | 479 | 479 | passed |

| Dataset / interface | Cases |
| --- | --- |
| SHAKE-128-FIPS202 | 269 |
| SHAKE-256-FIPS202 | 41 |
| ML-DSA-keyGen-FIPS204 | 25 |
| ML-DSA-sigGen-FIPS204/pure | 30 |
| ML-DSA-sigGen-FIPS204/preHash | 30 |
| ML-DSA-sigVer-FIPS204/pure | 15 |
| ML-DSA-sigVer-FIPS204/preHash | 15 |
