# ML DSA research

This is an independently written portable C implementation of ML DSA 44 derived from [FIPS 204](https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.204.pdf) and its [NIST errata](https://csrc.nist.gov/files/pubs/fips/204/final/docs/fips-204-potential-updates.xlsx). It provides seeded key generation, pure signing and verification with contexts, and HashML DSA signing and verification from caller-supplied digests. The caller supplies key seeds, signing randomness, and any prehash digest; the core does not acquire randomness or call a host hash library.

Official NIST ACVP vectors validate SHAKE, key generation, pure and prehash signing, and valid and invalid verification. The [algorithm map](docs/fips204.md), [arithmetic bounds](docs/arithmetic.md), and [constant time audit](docs/ct.md) describe the current implementation and its limits. This is research code, with no claim of side channel resistance or FIPS validation.

Run `make test model shake sample keygen sign verify prehash` after installing GCC and Python 3. `make vectors` downloads NIST ACVP files at a pinned commit into ignored `build/nist`. For the optional black box comparison, run `python3 -m pip install --target build/oracle --only-binary=:all: pqcrypto==1.0.0` and then `make differential`.

Cortex M4 support comes next. Algebraic NTT fault defenses are future stages; no protection result is claimed here.
