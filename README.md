# Algebraic checks for the ML DSA NTT

This repository implements ML DSA 44 from [FIPS 204](https://csrc.nist.gov/pubs/fips/204/final) in portable C and compares two algebraic defenses for its forward Number Theoretic Transform (NTT): the construction of [Abdelmonem et al.](https://eprint.iacr.org/2025/170) and our deterministic construction using an intermediate transform boundary. All three variants share the same key generation, signing, verification and baseline NTT implementation.

## What the checks do

The NTT maps a coefficient vector `p` to `y = T p` over the field modulo `q`; ML DSA 44 uses `n=256` and `q=8380417`. A checksum row on the input can be matched with a row on the output: if `b = Tᵀ a`, then `bᵀp = aᵀy` for every correct transform. We use two such equalities:

```text
sum(p[i])              = sum(a[i]     * y[i])  mod q
sum(beta[i] * p[i])     = sum(alpha[i] * y[i])  mod q
```

The wrapper computes the two expected input sums, executes the NTT once, and compares the two output sums. A mismatch returns an error. The first input row is all ones. The generated rows satisfy `Tᵀa = 1` and `Tᵀalpha = beta`; the NTT result is unchanged when the checks pass.

A unit additive deviation at a transform wire produces output error vector `v_r` and checksum responses `A_r = aᵀv_r`, `B_r = alphaᵀv_r`. Two faults cannot cancel both checks when every distinct wire pair satisfies

```text
A_r * B_s - A_s * B_r != 0  mod q.
```

Both implementations certify this condition for every pair of array slots at every forward NTT layer boundary. The guarantee covers at most two additive field deviations with trusted checker arithmetic, weights and control flow. It does not protect the inverse NTT, SHAKE or the entire signing process. [Threat model](docs/threat_model.md).

## How the constructions differ

**Prior construction.** Abdelmonem et al. choose the second row in output coordinates, recursively avoiding values that would make a pair determinant vanish. Half of the output weights are fixed to one. Our independently written implementation follows that construction, including its cheaper handling of unity weights. [Implementation details](docs/prior_checker.md).

**Our construction.** Put checksum variables at boundary `k`, propagate each modeled wire to that boundary, and normalize its response by `A_r`. For each pair, the difference of normalized responses is a nonzero linear form. Assign that constraint to its greatest nonzero coordinate, visit coordinates in increasing order, and choose the smallest field value that none of the current constraints forbids. Finally derive the input/output rows. Boundary `k` is used during coefficient generation; there is no additional intermediate check during execution. [Construction and complexity](docs/our_checker.md).

### Asymptotic improvement

For `n = 2^h` and `M = n(h+1)` modeled wires, the prior sufficient field-size threshold is

```text
(2n - 1)M = Θ(n² log n).
```

Our sufficient threshold is

```text
K(k) = 2^(k+1) + 2^(h-k+1) - 3
D(k) = K(k)M - K(k)(K(k)+1)/2.
```

At a balanced boundary, `K = Θ(√n)` and `D = Θ(n^(3/2) log n)`: the sufficient threshold improves by a factor `Θ(√n)`. These are bounds guaranteeing construction, not lower bounds on the smallest field admitting two checks. Both runtime checkers still add `Θ(n)` field operations to the `Θ(n log n)` NTT. Our current row uses more products and storage than the prior row.

## Measurements and graphs

The QEMU comparison runs matched Cortex M4 builds at `-O2` and `-O3 -flto`, counts guest instructions inside calibrated regions, and checks complete key/signature transcripts across all variants. The prior column measures this repository's implementation of the paper's construction, not the paper's reported machine timings.

QEMU TCG is not a Cortex M4 cycle model. Its instruction counts provide a reproducible simulation comparison; **a physical cycle-based speedup has not been measured**. Real DWT cycle and stack measurements remain pending. [Measurement method](docs/qemu_benchmark.md).

<!-- benchmark-results:start -->

For ML DSA (`n=256`, `h=8`, `k=4`), the sufficient threshold falls from **1,177,344** to **138,653**, an **8.49×** reduction. Both rows pass the same exhaustive pair certificate.

![Sufficient construction thresholds](docs/figures/construction_bound.png)

Forward NTT median guest-instruction counts, 101 observations per build and variant:

| Build | Baseline NTT | Prior NTT | Our NTT | Our vs prior |
| --- | ---: | ---: | ---: | ---: |
| `-O2` | 96,999 | 149,082 | 155,996 | +4.64% |
| `-O3 -flto` | 80,139 | 124,927 | 131,576 | +5.32% |

With `-O3 -flto`, our current protected NTT uses **5.32% more guest instructions** than the prior checker. This measures the compiled implementations; it does not establish a physical cycle improvement.

![QEMU NTT instruction counts](docs/figures/qemu_ntt.png)

![QEMU ML DSA instruction counts](docs/figures/qemu_mldsa.png)

| Variant | Extra field multiplications | Extra field additions | Constant table bytes |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 0 | 0 | 0 |
| Prior | 640 | 1024 | 2560 |
| Our construction | 768 | 1024 | 3072 |

[Raw observations](bench/qemu_benchmark.json) · [Complete statistics](docs/qemu_results.md) · [CSV](bench/qemu_benchmark.csv). Plots are generated by `tools/plot_benchmarks.py`; no QEMU count is presented as a hardware cycle.
<!-- benchmark-results:end -->

## Build and reproduce

```sh
make baseline prior our                 # host correctness and modeled-fault tests
make qemu-benchmark                    # ARM builds, QEMU measurements, graphs
python3 tools/plot_benchmarks.py        # redraw from saved raw results
```

The benchmark needs Python with Matplotlib, GCC, ARM GNU GCC/Newlib and QEMU with TCG plugin support. It honors `ARM_CC`, `ARM_INC`, `ARM_LIB`, `ARM_SIZE`, `ARM_NM`, `QEMU` and `QEMU_LIBDIR`; it also recognizes the toolchain extracted under `build/toolchain/root`. The pinned plugin API header is downloaded once into `build/qemu-benchmark/deps`.

Select a scheme library with `make build/libmldsa.so`, `make build/libmldsa_prior.so` or `make build/libmldsa_our.so`. Callers supply seeds and signing randomness and must check return statuses. HashML DSA accepts caller-supplied digests. Only the 44 parameter set is implemented; official vector tests do not constitute FIPS validation or a side channel assessment.

Both [exact certificates](docs/comparison.md) exhaustively check the concrete rows and pair determinants. `make comparison` reproduces the focused host/ARM comparison; `make thesis` runs the comprehensive official-vector and regression suites. [Reproduction commands](docs/reproduction.md), [thesis tables](docs/thesis_results.md), [implementation methodology](docs/implementation_methodology.md), [physical board setup](hardware/README.md).

## Formal checks

CBMC with Z3 checks modular arithmetic, butterfly/layer updates, array bounds, representation ranges and checker accumulation under documented contracts. All 29 recorded jobs passed, including unwinding assertions. These are portable C component proofs, not a proof of all ML DSA, SHAKE or ARM machine code. [Properties and assumptions](docs/verification.md).
