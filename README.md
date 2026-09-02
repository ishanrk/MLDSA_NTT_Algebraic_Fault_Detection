# ML DSA 44: NTT checker research

An independently written [FIPS 204](https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.204.pdf) ML DSA 44 implementation in portable C, with a Cortex M4 build path and three selectable forward NTT variants:

- **Baseline:** the unprotected transform.
- **Prior checker:** the [Abdelmonem et al. algebraic NTT defense](docs/prior_checker.md), independently derived from [ePrint 2025/170](https://eprint.iacr.org/2025/170).
- **Our checker:** the [deterministic intermediate boundary checksum construction](docs/our_checker.md).

Both defenses have exact certificates for every modeled wire pair. [Focused CBMC verification](docs/verification.md) covers arithmetic, butterfly and layer updates, loop safety and compositional checksum computation. The three variants pass compact Cortex M4 tests in QEMU. **Real hardware benchmarks are pending;** [physical-stage software](hardware/README.md) provides explicit F411RE/F446RE reference builds, DWT/stack sampling, flashing/capture and report generation. Mathematical coverage applies to the documented additive wire fault model with trusted checker arithmetic and control flow; no physical fault resistance is claimed.

## Reproduce the comparison

With the [required host, ARM, QEMU and CBMC tools](docs/reproduction.md) installed:

```sh
make comparison
```

This runs compact tests, both exact certificates, focused formal checks and matched ARM builds. It generates [machine readable results](bench/comparison.json), a [Markdown comparison](docs/comparison.md) and [LaTeX tables](bench/comparison.tex). Physical cycle, flash, RAM and stack fields remain pending. No board is required for this command.

For a quick host check:

```sh
make baseline prior our
```

## Thesis artifact

The [thesis results](docs/thesis_results.md) and [LaTeX fragments](bench/thesis/tables.tex) are generated from [one frozen raw dataset](bench/thesis.json). The final comprehensive host regression covers all supported official vectors for all three variants under GCC, Clang, ASan and UBSan, both exact certificates, focused CBMC proofs and compact QEMU execution. Physical cycles, stack and board smoke tests remain pending; linked reference-image sizes are available.

```sh
make thesis
```

This is the full regression command, intended for a final milestone rather than routine edits. [Final reproduction](docs/thesis_reproduction.md) records dependencies, scope and physical-capture import. [Implementation methodology](docs/implementation_methodology.md) supplies methods text; the [threat model](docs/threat_model.md) states the additive boundary-wire guarantee and trusted components. Physical cost measurements do not establish general physical fault resistance.

## Implementation and evidence

The shared scheme supports seeded key generation, pure signing and verification with contexts, and HashML DSA from caller-supplied digests. Callers supply key seeds and signing randomness and must check return statuses. Select a scheme variant with `make build/libmldsa.so`, `make build/libmldsa_prior.so` or `make build/libmldsa_our.so`; signing and verification use the same implementation.

Official NIST ACVP vectors validate SHAKE, key generation, pure/prehash signing and valid/invalid verification. The [algorithm map](docs/fips204.md), [arithmetic bounds](docs/arithmetic.md), [constant time audit](docs/ct.md), [Cortex M4 notes](docs/cortexm4.md) and [formal scope](docs/verification.md) describe the implementation and its limits. This is research code, with no claim of FIPS validation or side channel resistance.

The [reproduction guide](docs/reproduction.md) gives individual generation, certificate, proof, cross compilation and QEMU commands. It also explains tool overrides and how to regenerate thesis tables from the same raw data.

The larger individual validation targets remain available through `make test model shake sample keygen sign verify prehash`. `make vectors` downloads pinned NIST ACVP data into ignored `build/nist`. `make thesis` includes the comprehensive final run; the focused `make comparison` remains available for compact reproduction.
