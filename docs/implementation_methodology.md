# Implementation and experimental methodology

The portable C implementation has three selectable forward NTT variants, shared scheme operations and separate coefficient generation, certificate and experiment tools. Numerical results are generated from raw records in [thesis_results.md](thesis_results.md) and [qemu_results.md](qemu_results.md). Physical DWT/stack measurements remain unmeasured.

## Independent ML DSA implementation

The portable C implementation follows the ML DSA 44 algorithms in [FIPS 204](https://csrc.nist.gov/pubs/fips/204/final), with the function mapping in [fips204.md](fips204.md). It implements seeded key generation, pure signing and verification with contexts, and HashML DSA using a digest supplied by the caller. The caller supplies the key seed and signing randomness and must check return statuses. Only the 44 parameter set is implemented. Supporting these algorithms and passing vectors is not a claim of FIPS validation.

Polynomial arithmetic, encoding, rounding, sampling, matrix/vector operations and the scheme operations are shared by all three builds. `MLDSA_PRIOR_CHECKER` and `MLDSA_OUR_CHECKER` select the forward transform wrapper through `mldsa44_ntt`; neither macro selects a different signing or verification algorithm. The inverse transform and directly sampled matrix entries are unprotected. The C implementation was written independently; official expected outputs and the pqcrypto implementation are used as test oracles, not as production code dependencies.

SHAKE128/256 are implemented from FIPS 202 in `src/shake.c`. The final functional suite exercises SHAKE vectors and streaming boundaries, but SHAKE and the complete signing algorithm are outside the focused formal verification scope. The [constant time audit](ct.md) records unresolved timing and memory access concerns. No constant time or side channel resistance claim is made.

## NTT representation and ordering

`src/poly.c` uses canonical residues modulo `q=8380417`; centered values are converted explicitly when required by scheme operations. Modular multiplication forms a 64 bit product and reduces it before reuse. The implementation does not use Montgomery or lazy residues. Caller ranges and intermediate bounds are documented in [arithmetic.md](arithmetic.md).

`src/ntt.c` implements the fully split length 256 negacyclic radix two transform. Forward layers have butterfly distances 128 through 1, with twiddles consumed in the production table order. The inverse visits distances 1 through 128 and applies the inverse length scale. The table generator derives the powers of the standard root and checks roots and output ordering. The independent Python model compares the C transform with polynomial evaluation; the C tests compare inverse round trips and polynomial products against schoolbook multiplication.

The same production layer ordering, wire numbering, twiddles and output permutation define the checker network. A modeled location is `r=256*l+i`, where `l` ranges from the input boundary through all eight completed layers and `i` is the physical array index. The generator models every location, including the output boundary, without introducing a differently ordered abstract transform.

## Prior checksum defense

The prior variant independently implements the two check construction of [Abdelmonem, Holzbaur, Raddum and Zeh](https://eprint.iacr.org/2025/170) for this production transform. `tools/gen_prior_checker.py` derives the rows and emits `src/prior_tables.inc`. Its output coordinate construction fixes the prescribed subset of second check weights to one and deterministically assigns the remaining weights. Implicit unity coefficients are omitted from storage. This is this repository's implementation of the published construction, not the authors' performance results.

For input column `p` and transform `T`, the ordinary coefficient sum is the first input check. The output rows `a,alpha` and input rows `b,beta` satisfy `b=T^T*a` and `beta=T^T*alpha`, with `b` all ones. `src/prior.c` computes both expected input sums, invokes the baseline forward NTT once, and compares both output sums. A mismatch returns an error which the shared scheme code propagates. The transform result must be discarded on failure.

## Deterministic intermediate boundary construction

`tools/gen_our_checker.py` places variables at boundary `k=4` of the same network. Normalized fault responses become linear forms `W_r(u)`. For each distinct pair it forms `H_rs=W_r-W_s` and assigns that constraint to its greatest nonzero coordinate. Coordinates are visited in increasing order. Previously chosen coordinates make each assigned constraint forbid one field value; the generator chooses the smallest allowed value and does not scan the full field.

The sufficient bound uses `M=n(h+1)`, `K(k)=2^(k+1)+2^(h-k+1)-3`, and `D(k)=K(k)M-K(k)(K(k)+1)/2`. The generator checks the concrete values and `q>D(k)`, derives both final rows from the intermediate assignment, and chooses the smallest permitted shift by the first row if needed to make every second response nonzero. No random search or hand selected final row is used. The checked in tables are generated output.

Boundary 4 is used for offline construction only. `src/our.c` performs the same four input/output checksum accumulations around one baseline NTT call as the prior wrapper. It has no runtime intermediate boundary check. The improvement concerns a sufficient construction bound; the current straightforward implementation's operation and storage costs must be read from generated tables. A lower field size bound does not establish a speedup.

## Exact certificates

Both generators independently check row identities through evaluation and graph pullback, unit wire propagation against the production network, nonzero response conditions and every distinct pair determinant. The current generator additionally checks intermediate propagation and explicitly records duplicate normalized responses. The prior generator checks ratio distinctness internally but stores no separate duplicate ratio counter. The generated table preserves this difference.

The coefficient SHA256 serializes full `b,a,beta,alpha` rows as little endian 32 bit words in production order, including implicit unity weights. The network digest covers the ordered butterfly triples. `--check` recomputes the construction and certificate and requires byte identity with both repository outputs. This is an exact finite field computation for a concrete instance. It does not formally verify the Python generator or replace the general theorem proof.

## Focused formal verification

CBMC with Z3 checks portable C components using a 32 bit little endian model with i386 preprocessing. Arithmetic jobs call the actual production functions. Butterfly, layer and checksum step jobs use structurally checked source views of the actual production regions; arithmetic contracts are proved separately. Full loop harnesses check bounds, pointer/index behavior, representation ranges and wrapper output preservation under canonical value contracts. Every job enables unwinding assertions and has an individual timeout.

Preconditions are valid, full sized, live objects with the documented nonoverlap contract; canonical field inputs; centered inputs within their stated range; and symbolic indices selecting actual production pairs. Canonical contract results and side effect free replacements are compositional assumptions whose scope is documented. See [verification.md](verification.md) for every production function, command, unwind bound and assumption.

Checksum accumulation correctness combines zero initialization, an arbitrary index step, verified modular arithmetic and the loop structure. No fault acceptance combines these implementation lemmas with exact row identities and inspected transform composition. The complete transform/checksum refinement is not assembled into one automatically checked global proof. No claim covers the whole ML DSA standard, SHAKE, ARM instructions, startup, peripheral drivers, in place pointwise aliasing or physical faults.

## Cortex M4 and benchmark method

The portable Cortex M4 cross build uses Thumb and the soft float ABI. QEMU `mps2-an386` runs the compact deterministic correctness suites. It validates emulator execution and selected test injections. A separate [TCG plugin benchmark](qemu_benchmark.md) counts guest instructions in matched optimized builds; those counts are not physical cycles.

The separate physical firmware has explicit NUCLEO F411RE and NUCLEO F446RE reference profiles, independent startup/linker/UART code, a nominal HSI clock configuration and polling serial output. Profiles do not identify a connected board. The acquisition tool checks target registers and identity, flashes all three compact images, requires their recorded expected outputs, then acquires benchmarks. Exact board/core, compiler, flags, ELF/source digests, clock register observations, ST Link method and serial method are captured with the run. See [hardware/README.md](../hardware/README.md) and [ST's board manual](https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf).

DWT measurements use the same fixed schedules across variants, keep printing outside timed regions, calibrate timer read overhead, and preserve all raw and corrected samples. The signing schedule varies supplied randomness with a fixed key, exercising rejection variability. Each operation reports count, minimum, median, maximum and nearest rank P95. Overhead uses baseline medians. The acquisition guard establishes intervals shorter than counter wrap; unavailable counters produce no observations.

Flash and static RAM are linked ELF sizes, with readonly tables included in text and stack excluded from static RAM. Watermarks include the caller and callee stack frames over every scheduled sample. They are observed high water, not an exhaustive worst case bound. GCC individual frame reports are separate static observations and do not establish the complete call stack bound. Current F401RE memory limits exclude it from these unchanged benchmark profiles.

Physical Cortex M4 measurements establish execution and memory cost for the recorded board, build and inputs. They do not by themselves establish resistance against every real physical fault mechanism. No physical cycle, stack or board correctness number is inferred from synthetic host controls or from QEMU.

## Final evidence collection

`make thesis` runs the existing comprehensive C suites once per host compiler/sanitizer mode, all supported official vectors for each scheme variant, the existing differential test once per GCC variant, constants checks, both exact certificates, focused formal jobs, matched ARM builds, compact QEMU tests and offline benchmark tool controls. It verifies NIST inputs against a manifest of official blobs pinned to the fetcher's commit. Unsupported parameter sets, internal signature interfaces and bit oriented SHAKE vectors are counted as excluded, rather than passed.

The runner freezes commands, logs' digests, actual case counts, tool versions, source/ELF digests, certificates and formal records in `bench/thesis.json`. One renderer emits the Markdown results and independent LaTeX fragments. Without physical captures, hardware results remain pending and the hardware milestone is incomplete. Supplying a completed manifest validates recorded captures; it does not execute a new physical acquisition. [thesis_reproduction.md](thesis_reproduction.md) describes the final commands and remaining manuscript work.
