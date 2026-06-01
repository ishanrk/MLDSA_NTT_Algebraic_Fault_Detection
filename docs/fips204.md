# FIPS 204 algorithm map

The semantic sources are [FIPS 204](https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.204.pdf), its [official potential updates](https://csrc.nist.gov/files/pubs/fips/204/final/docs/fips-204-potential-updates.xlsx), and [FIPS 202](https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.202.pdf) for SHAKE. The algorithm numbers below are from FIPS 204. The implementation supports the 44 parameter set. Polynomial and NTT values use canonical residues at function boundaries; see [arithmetic.md](arithmetic.md).

| Algorithms | Function | Notes |
| --- | --- | --- |
| 1, 6 | `mldsa44_keygen` | Explicit 32-byte seed; encodes public and secret keys. |
| 2, 7 | `mldsa44_sign`, `sign_core` | External pure message and context; explicit 32-byte `rnd`; standardized rejection loop. |
| 3, 8 | `mldsa44_verify`, `verify_core` | Pure message; checks lengths, z norm, hint encoding and challenge. |
| 4, 5 | `mldsa44_sign_digest`, `mldsa44_verify_digest` | Prehash digest supplied by caller; DER OID and domain separator assembled in `mldsa44_representative`. |
| 9-13 | `pack`, `mldsa44_unpack_bits`, `mldsa44_representative` | Bit and byte conversion is inlined at use sites. |
| 14, 30 | `sample_ntt` | Three-byte coefficient rejection. |
| 15, 31 | `sample_eta` | Half-byte bounded rejection. |
| 16-19 | `pack`, `mldsa44_unpack_bits` | Canonical bit encodings for polynomial coefficients. |
| 20, 21 | `mldsa44_sig_encode`, `mldsa44_sig_decode` | Ordered sparse hints and canonical zero padding. |
| 22, 23 | `mldsa44_pk_encode`, `mldsa44_pk_decode` | Public seed and high bits. All 10-bit coefficient values are valid. |
| 24, 25 | `mldsa44_sk_encode`, `mldsa44_sk_decode` | Secret seed, hashes, small vectors and low bits; eta codes 5-7 are rejected. |
| 26-28 | `mldsa44_sig_encode`, `mldsa44_sig_decode`, `mldsa44_w1_encode` | Signature and commitment encodings. |
| 29 | `mldsa44_sample_ball` | Sparse challenge polynomial. |
| 32-34 | `mldsa44_expand_a`, `mldsa44_expand_s`, `mldsa44_expand_mask` | Matrix, secret and mask sampling. |
| 35-40 | `mldsa44_power2round`, `mldsa44_decompose`, `mldsa44_highbits`, `mldsa44_lowbits`, `mldsa44_make_hint`, `mldsa44_use_hint` | Rounding and hint arithmetic. |
| 41-48 | `mldsa_ntt_forward`, `mldsa_ntt_inverse`, `tools/gen_zetas.py`, `mldsa_ntt_mul`, `mldsa44_matvec` | Bit reversed transform and NTT arithmetic. |

FIPS 204 also gives a Montgomery reduction appendix; this implementation uses canonical residues and direct modular reduction instead. FIPS 202 Keccak-f[1600] and SHAKE128/256 are in `src/shake.c`. `tools/gen_keccak.py` derives round constants and rotation offsets. Regenerate the checked-in tables with `python3 tools/gen_zetas.py` and `python3 tools/gen_keccak.py`; add `--check` to verify them without writing.

`tools/fetch_nist.py` pins `usnistgov/ACVP-Server` commit `975de31eb83d87039ec88934fdc47d8c312b892d` and fetches only prompt and expected-result JSON into ignored `build/nist`. Tests cover 25 key-generation, 30 pure signing, 15 pure verification, 30 prehash signing, 15 prehash verification, 269 SHAKE128 and 41 SHAKE256 official cases. The prehash tests calculate digests with Python `hashlib`; the C API requires callers to choose the matching hash and provide its digest. NIST ACVP supplied SHA-2, SHA-3 and SHAKE cases, with byte-for-byte signature reproduction.
