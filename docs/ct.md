# Constant time audit

This stage has not established constant time behavior. The locations below need review before using keys against a side channel adversary. The portable C result is compiler- and target-dependent.

## Public control flow

- `mldsa44_verify` and `verify_core` reject lengths, malformed hints, z bounds, and challenge mismatches. The key and signature are normally public, but the message or a bearer-token signature may be confidential in some applications.
- `mldsa44_sign_digest` and `mldsa44_verify_digest` select digest size and domain encoding from the caller's public hash identifier. Context and message lengths also control SHAKE work.
- `mldsa44_expand_a` and `sample_ntt` reject public matrix coefficients from the public seed `rho`.
- All NTT layer counts and matrix dimensions are fixed.

## Standardized rejection behavior

- `sign_core` repeats FIPS 204 Algorithm 7 until z, low bits, `ct0`, and hint weight pass their bounds. The number of attempts can depend on secret key material and signing randomness. This is inherent in the specified signing procedure, but needs leakage analysis.
- `sample_eta` rejects nibbles while constructing secret vectors. Its loop count depends on the secret seed.
- `mldsa44_sample_ball` rejects selected byte values while constructing the challenge. Its loop count depends on a challenge seed derived from secret signing state during signing.

## Potential secret dependent control flow

- `mldsa_add`, `mldsa_sub`, `mldsa_reduce`, and `mldsa_center` need generated-code inspection for branches and variable-latency division. They process secret coefficients during key generation and signing.
- `mldsa44_power2round`, `mldsa44_decompose`, `mldsa44_make_hint`, and `mldsa44_use_hint` branch or compare on coefficients. Key generation and signing pass secret-derived values.
- `mldsa44_norm` exits at the first failing coefficient; `sign_core` also branches on low-bit signs, rejection decisions and hint weight. The accepted signature does not reveal the individual failing position, but timing may.
- `pack` calls `mldsa_center` on secret and signature coefficients. `mldsa44_sk_decode` branches on invalid secret-key encodings. `mldsa44_sig_encode` branches on secret-derived hint bits.
- `sample_eta` and `sample_ntt` branch on sampled values. `sample_ntt` is public in this parameter set; `sample_eta` is secret.

## Potential secret dependent memory access

- `mldsa44_sample_ball` indexes `c->c[j]` using a sampled byte. During signing its seed is derived from secret state. This needs a constant time alternative or a justified leakage model before hardened use.
- `mldsa44_sig_encode` writes sparse hint positions according to secret-derived hint bits. The encoded signature later reveals those positions, but intermediate memory and timing still need review.

## Cortex M4 review points

- Inspect division and modulo lowering in `src/poly.c`, `src/round.c`, and NTT butterflies. Variable timing or library calls are possible.
- Measure stack frames in `mldsa44_keygen`, `sign_core`, and `verify_core`; the 4-by-4 NTT matrix alone is 16 KiB. No heap is used.
- Inspect rotations and 64-bit operations in `src/shake.c`; Keccak-f[1600] uses 25 64-bit lanes and may be costly on a 32-bit core.
- Inspect compiler output for conditional branches, table access, and spills in sampling, signing, and encoding. Current tests establish functional behavior only.
- Ensure an embedded caller supplies independent signing randomness. Reusing the same `rnd` with a key and message changes the standardized hedging behavior.

## Observed in the portable ARM build

With `arm-none-eabi-gcc` 10.3.1 at `-O2 -mcpu=cortex-m4 -mthumb -mfloat-abi=soft`, disassembly of the emulator baseline shows `mldsa_mul` calling `__aeabi_uldivmod` after `umull`. Its `__udivmoddi4` callee uses `udiv` and conditional branches. `mldsa_add` branches on its result; `mldsa_sub` uses conditional Thumb instructions. `mldsa44_norm` exits early, and `mldsa44_sample_ball` uses a sampled coefficient index for both a load and a store. The NTT calls modular multiplication inside each butterfly. These are generated-code observations, not timing or physical leakage measurements. The actual STM32 core revision, memory system, compiler options, and physical side-channel behavior remain unknown until the board is identified.
