# Code walkthrough and presentation notes

## One minute explanation

The signer computes a 256 coefficient NTT. A fault can corrupt it and expose the signing secret. We add a public five element random input mask, run the original NTT, remove the known transform of that mask, and compare six algebraic identities. A rank certificate bounds escape for specified faults, including complete zero twiddle corruption. A mismatch aborts before any signature is written.

## Source map

| File | What it does |
| --- | --- |
| `src/sign.c` | Existing signing loop. The optional NTT domain (z) formula reproduces Ravi's randomized attack setting. Protected nonce transforms share a mask. |
| `src/mldsa44_internal.h` | Dispatches to the baseline, either existing checker, or the new encoded checker. |
| `src/encoded.c` | Samples five field elements, computes expected moments, masks the input, runs the original NTT, removes the mask, and checks six output moments. |
| `src/encoded_tables.inc` | Public inverse permutation, output check matrix (H), and transformed mask matrix (V). |
| `tools/gen_encoded_tables.py` | Generates those tables from one fixed public permutation. |
| `tools/audit_encoded.py` | Recomputes the rank certificate and compares the C tables with the generator. |
| `src/ntt.c` | Existing butterfly code with a demo only hook at the twiddle load. |
| `demo/fault_demo.c` | Command line keygen, sign and verify, Linux random source, and fault selection by NTT call count. |
| `demo/run_demo.py` | Runs both attacks, the secret recovery, a new message forgery, and the protected replay. |
| `demo/attacker.py` | Reused single signature recovery for the randomized path. |
| `demo/derive_equivalent.py` | Reused ring arithmetic and equivalent secret key reconstruction. |
| `demo/bench_encoded.c` | Times single NTT calls and four input batches on the current host. |
| `demo/openssl_mldsa.c` | Optional independent OpenSSL 3.5 or newer verifier. |

## Construction and code

All calculations are in \(\mathbb F_q\) for \(q=8380417\). Let \(T\) be the original forward NTT. The generator shuffles coefficient positions using a public permutation \(\pi\) with seed `204256`, then defines

\[
W_{k,i}=\binom{\pi(i)}{k}\quad(0\le k<6),\qquad
U_{i,j}=\binom{\pi(i)+1}{j+1}\quad(0\le j<5),
\qquad H=WT^{-1},\quad V=TU.
\]

The C tables store only the inverse permutation, (H), and (V). `draw` obtains 20 random bytes, takes five independent 23 bit candidates, and redraws any value at least (q). Thus (r\in\mathbb F_q^5) is uniform if the source is uniform.

`run` evaluates the input mask (Ur) by Newton forward differences, and uses repeated suffix sums to compute the six input binomial moments (Wa) with mostly additions. For a single transform, it calls `check_one`. For the four fixed nonce inputs, it reuses the same input and output masks but computes and checks each NTT separately. On any failed check, `run` clears the output array and returns an error.

`check_one` copies (a+Ur) into a temporary polynomial, calls the original `mldsa_ntt_forward`, subtracts (Vr), and forms six output sums using 64 bit accumulation. The largest raw sum is below (256q^2<2^{64}), so reduction after accumulation is safe for correct field values. It accepts exactly when (H(b-Vr)=Wa). Without a fault, (b=T(a+Ur)), hence (b-Vr=Ta), and (HTa=Wa).

The five random values and all weights may be public. The guarantee instead needs the original input fixed before the random draw and an intact checker and abort path.

## What the audit proves

For a faulty linear NTT (F), acceptance requires

\[
H(F-T)Ur=-H(F-T)a.
\]

The audit verifies that the six by five matrix (H(F-T)U) has rank five when every twiddle is zero. In that model (F(x)=x_0\mathbf1). For each fixed input there is at most one accepted (r) out of (q^5).

At each of nine boundaries, the audit computes the remaining NTT map (B_l), the prefix map (A_l), and the six syndrome coordinates (HB_l e). It finds 2,304 nonzero single wire syndrome columns with no two proportional. Any harmful one or two arbitrary additive field errors among these locations is therefore detected. It also checks that every consecutive interval of up to six columns has full column rank.

For every longer interval (I), the audit checks rank five for (HB_l P_I A_l U). This bounds zeroization and nontrivial common scaling. For a common overwrite value selected after the mask is revealed, it checks rank six after adjoining the column (HB_l\mathbf1_I). That leaves at most one accepted mask per interval even if the attacker chooses that common value. There are 282,375 long intervals for each fault class, plus the complete zero twiddle event, giving the union bound (564751/q^5\). The attacker can select one catalog event after seeing (r). A shared mask for four NTTs needs an additional factor of four.

This certificate covers field arithmetic at the named boundaries. It does not classify the distribution of real glitches, multiple combined fault mechanisms, a corrupted checker, or statistical ineffective fault leakage.

## Deterministic attack

1. The runner uses `rnd=0`, generates a clean signature, and chooses a message with (c_0=0) that accepts on its first signing attempt.
2. It signs that message again with the same deterministic nonce. `fault_demo.c` replaces all 255 loaded challenge twiddle values with zero at forward NTT call 17. The resulting transform of (c) is zero.
3. It keeps a pair only if the faulted first attempt also accepts. The two (z) values share (y) and (c), while (z=y+c s_1) and (z^*=y).
4. The attacker computes (s_1=c^{-1}(z-z^*)). Only afterward does the runner compare the 1,024 recovered coefficients with the victim key.
5. The attacker's `derive_equivalent.py` uses recovered (s_1), public (A), and public (t_1) to choose short (s'_2) and compatible (t'_0). A different message is signed with this alternate key and accepted under the original public key.
6. Replaying the zero twiddle fault with `MLDSA_ENCODED_CHECKER` aborts at call 17. The faulted deterministic signature itself does not verify, while the new forged signature does.

## Randomized attack

1. The runner checks that the optional `MLDSA_NTT_DOMAIN_Z` formula produces byte identical clean signatures to the ordinary formula under a shared seed. Each attack request then uses fresh signing randomness.
2. The hook zeroes all twiddles in the first four nonce NTT calls, numbered 13 through 16. If the faulted attempt rejects, the runner makes a new request with fresh randomness.
3. A released faulty signature verifies because both (w) and (z) use the same corrupted nonce NTT. `attacker.py` receives only that signature. All but the constant coefficient of (c s_1) are visible in (z^*).
4. The attacker enumerates the missing coefficient in ([-78,78]), inverts the public challenge (c), and keeps the unique (s_1) whose coefficients lie in ([-2,2]). A new message forgery verifies as above.
5. The protected four input batch detects the first corrupted nonce NTT and aborts before a signature is written. Its clean output is byte identical to the ordinary output.

The four software fault selections reproduce the algebraic collapse. They do not recreate the paper's physical pointer fault or establish one pulse propagation on this implementation.

## Likely interview questions

**Is this checksum based?** Yes. It is public randomized encoding paired with six algebraic checks. Its exact construction and comparative novelty still require a literature audit.

**Why does the randomized attack use a different (z) path?** The original `z=y+c*s1` formula does not consume the faulty nonce NTT in (z). Ravi's attack assumes `z=INTT(NTT(y)+NTT(c)*NTT(s1))`. Both agree when there is no fault.

**Does the attacker need a secret mask?** No. The bound allows the attacker to inspect the mask, then choose one event from the certified finite catalog.

**What happens if the checker is faulted?** That is outside this model. The abort decision and the saved input must retain integrity.

**Does this beat recomputation?** The current C batch does not show a speed advantage. Benchmark on the presentation host and state the result as a host measurement. This new checker has no Cortex M4 measurement.

**How does it relate to the older thesis checker?** It is another opt in wrapper at the existing NTT dispatch point. The original two check code and theorem remain separate and unchanged.
