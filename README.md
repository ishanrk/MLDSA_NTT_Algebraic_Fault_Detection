# Algebraic fault detection for the ML DSA NTT

The current method constructs two algebraic checks that detect every nonzero result error caused by at most two additive faults at modeled NTT boundary wires. It is implemented inside an independently written ML DSA 44 implementation of [NIST FIPS 204, Module Lattice Based Digital Signature Standard](https://csrc.nist.gov/pubs/fips/204/final). The project includes key generation, signing, verification, message formatting, polynomial arithmetic and SHAKE, with portable C and an ARM Cortex M4 build path.

Baseline, prior method and current method share the same cryptographic implementation. Only the forward NTT wrapper changes. Validation includes official NIST vectors, malformed input tests, exact algebraic certificates, focused CBMC proofs and reproducible QEMU benchmarks. The implementation methodology is in [docs](docs/implementation_methodology.md); test results do not constitute FIPS validation.

## NTT fault analysis

ML DSA uses polynomial multiplication over the ring `Z_q[X]/(X^n+1)`, with `n=256` and `q=8380417`. The Number Theoretic Transform maps coefficients to a representation where multiplication is pointwise. Its butterfly network repeatedly mixes pairs of coefficients, so a fault at an internal wire can spread to several output coefficients.

Prasanna Ravi, Bolin Yang, Shivam Bhasin, Fan Zhang and Anupam Chattopadhyay demonstrated attacks involving NTT twiddle corruption in [Fiddling the Twiddle Constants: Fault Injection Analysis of the Number Theoretic Transform](https://eprint.iacr.org/2022/824). Such physical faults can affect many wires. The algebraic model used here concerns additive deviations at data wires, with trusted twiddles, checker arithmetic and control flow.

For a transform of length `n=2^h`, every array slot at each of the `h+1` layer boundaries is a modeled location. There are `M=n(h+1)` locations. A unit deviation at location `r` propagates to output vector `v_r`; a fault of magnitude `delta` adds `delta*v_r` to the output. The protection covers the forward NTT. Inverse transforms, SHAKE and faults in the checker are outside this model. [Fault model](docs/threat_model.md).

## Algebraic checks

Write the correct transform as `y=T*p`. An output checksum row `a` and input row `b` satisfy

$$
b=T^{\mathsf T}a,
\qquad b^{\mathsf T}p=a^{\mathsf T}y \pmod q.
$$

The checker computes the expected input sum, runs the NTT once and compares it with the weighted output sum. A mismatch rejects the result. This avoids a second transform.

### Single fault

The response to one deviation is

$$
A_r=a^{\mathsf T}v_r,
\qquad d_r=\delta A_r \pmod q.
$$

A nonzero fault is detected whenever `A_r` is nonzero at every modeled location. Sven Bauer, Fabrizio De Santis, Kristjane Koleci and Anita Aghaie developed a single fault defense using polynomial evaluation and interpolation in [A Fault Resistant NTT by Polynomial Evaluation and Interpolation](https://eprint.iacr.org/2024/788).

Mohamed Abdelmonem, Lukas Holzbaur, Håvard Raddum and Alexander Zeh generalized the checksum conditions in [Efficient Error Detection Methods for the Number Theoretic Transforms in Lattice Based Algorithms](https://eprint.iacr.org/2025/170). For the completely split transform used by Dilithium, the first input checksum can be the ordinary coefficient sum. This repository derives its output row from the exact production NTT order.

### Two faults

One equality can miss two faults when their checksum responses cancel. Add a second row `alpha`, with input row `beta=T^T*alpha`, and define `B_r=alpha^T*v_r`. Every distinct pair must satisfy

$$
\Delta_{rs}=A_rB_s-A_sB_r\ne0 \pmod q.
$$

The two response columns are then independent, so two nonzero magnitudes cannot cancel both checks. Since every `A_r` is nonzero, the equivalent condition is that every ratio `B_r/A_r` is distinct. Abdelmonem et al. give this criterion and a deterministic two check construction for Dilithium in the [same paper](https://eprint.iacr.org/2025/170).

The prior method assigns output weights recursively while avoiding zero pair determinants. Half of its second output weights are one, reducing the extra products to `2.5*n`. The implementation follows the paper's construction and stores only the remaining weights. [Prior method](docs/prior_checker.md).

The production wrapper compares these two equations modulo `q`:

$$
\sum_i p_i=\sum_i a_i y_i,
\qquad \sum_i\beta_i p_i=\sum_i\alpha_i y_i.
$$

## Current construction

The current method places construction variables at an intermediate boundary `k`. A fault before that boundary is propagated forward; a fault after it is mapped back through inverse butterflies. Normalize each resulting linear response `W_r(u)` by the first checksum response. For each location pair, construct `H_rs(u)=W_r(u)-W_s(u)`.

1. Assign each nonzero difference form to its greatest nonzero coordinate.
2. Visit coordinates in increasing order. Each assigned form forbids one field value at its last coordinate.
3. Collect those values and choose the smallest value absent from the set.
4. Derive the final input and output rows. If needed, add a multiple of the first row to make every second response nonzero; pair determinants are preserved.

The generator uses sparse wire propagation, groups constraints by their last coordinate and updates partial response values as coordinates are chosen. The field search takes at most the number of forbidden values plus one membership checks. It does not enumerate all `q` values or use random search. Boundary `k` is used during coefficient generation; execution still has two input/output equalities around one NTT. [Algorithm and complexity](docs/our_checker.md).

### Construction bound

The prior sufficient field condition is `q>(2*n-1)*M`, with threshold

$$
(2n-1)M=\Theta(n^2\log n).
$$

The intermediate support bound gives

$$
K(k)=2^{k+1}+2^{h-k+1}-3,
\qquad D(k)=K(k)M-\frac{K(k)(K(k)+1)}{2}.
$$

At a balanced boundary `k=floor(h/2)`,

$$
K(k)=\Theta(\sqrt n),
\qquad D(k)=\Theta(n^{3/2}\log n).
$$

The sufficient threshold improves by a factor $\Theta(\sqrt n)$. These are construction guarantees. Both execution wrappers still add $\Theta(n)$ field operations to a $\Theta(n\log n)$ NTT.

<!-- construction-results:start -->

For `n=256`, `h=8` and `k=4`, the generator verifies `M=2304`, `K=61`, `D=138653` and `q=8380417>D`.

| Method | Sufficient threshold |
| --- | ---: |
| Prior method | 1,177,344 |
| Current method | 138,653 |

The sufficient threshold is **8.49 times smaller**. Both methods certify all **2,653,056** location pairs with zero determinant failures.

![Construction bound at transform length 256](docs/figures/construction_bound.png)
<!-- construction-results:end -->

The exact certificates verify the checksum row identities, every modeled wire response and every pair determinant. A single fault is covered by the first nonzero response; two faults are covered by the pair condition. Exact cancellation at one wire produces no result error. The certificates establish coverage in this field model, rather than resistance to every physical fault mechanism. [Certificates](docs/comparison.md).

## Reproduction and C verification

```sh
make baseline prior our
make qemu-benchmark
python3 tools/plot_benchmarks.py
```

The benchmark needs Python with Matplotlib, ARM GCC with Newlib and QEMU with TCG plugin support. [Reproduction commands](docs/reproduction.md) include generators, exact certificates, compiler and sanitizer runs, ARM builds and tool overrides. [Thesis tables](docs/thesis_results.md) are generated from raw repository data.

CBMC with Z3 checks the portable C arithmetic, butterfly and layer updates, memory bounds, representation conversions and checksum accumulation under documented preconditions. All 29 recorded jobs passed with unwinding assertions enabled. The proof scope excludes full ML DSA, SHAKE and ARM machine code. [Properties and assumptions](docs/verification.md).

## ARM Cortex M4 measurements and optimization

Matched builds use ARM GCC at `-O2` and `-O3 -flto`. The optimized configuration enables compiler optimization and link time optimization across the shared arithmetic and checker code. The first input row is implicit ones; the prior method also skips multiplication by its unity output weights. Generated tables are read only. The current checksum arithmetic uses three full weighted rows.

QEMU runs the same inputs for each method and counts guest instructions between calibrated markers. A fixed assembly control checks the counter, and complete public key/signature transcripts must match across all six builds. These counts measure compiled instruction execution. QEMU does not model Cortex M4 instruction latency or flash wait states, so physical DWT cycles and measured stack remain pending. [Benchmark method](docs/qemu_benchmark.md), [physical target](hardware/README.md).

<!-- benchmark-results:start -->

Forward NTT median guest instruction counts, 101 observations per build and method:

| Build | Baseline | Prior method | Current method | Current vs prior |
| --- | ---: | ---: | ---: | ---: |
| `-O2` | 96,999 | 149,082 | 155,996 | +4.64% |
| `-O3 -flto` | 80,139 | 124,927 | 131,576 | +5.32% |

At `-O3 -flto`, the current method executes **5.32% more instructions** than the prior method. Its construction guarantee improves; this implementation has no measured cycle improvement.

![Forward NTT instruction counts](docs/figures/qemu_ntt.png)

| Method | Instruction reduction from `-O2` to `-O3 -flto` |
| --- | ---: |
| Baseline | 17.38% |
| Prior method | 16.20% |
| Current method | 15.65% |

Key generation, signing and verification medians use the optimized configuration. Signing includes its ordinary rejection variability; the linked statistics retain minimum, median, maximum and P95.

![ML DSA instruction counts](docs/figures/qemu_mldsa.png)

| Method | Extra field multiplications | Extra field additions | Constant table bytes |
| --- | ---: | ---: | ---: |
| Baseline | 0 | 0 | 0 |
| Prior method | 640 | 1024 | 2560 |
| Current method | 768 | 1024 | 3072 |

[Raw observations](bench/qemu_benchmark.json), [complete statistics](docs/qemu_results.md) and [CSV](bench/qemu_benchmark.csv). Python generates the graphs and tables from the raw record.
<!-- benchmark-results:end -->

### GCC SMLALD patch

Ishan Kumthekar's ongoing [GCC patch](docs/compiler/gcc-smlald.patch) recognizes two packed signed halfword products accumulated into a `64` bit value. For the supplied Cortex M4 example, two `SMLALBB` instructions and two high half extractions become one `SMLALD`: the arithmetic sequence falls from `4` instructions to `1`, and the complete function from `7` to `4`.

The patch concerns packed `16` bit arithmetic. This ML DSA implementation uses canonical `32` bit field coefficients and was benchmarked with the recorded ARM GCC toolchain. Its results do not include a speedup from that patch. [Patch scope and recorded tests](docs/compiler/gcc_smlald.md).
