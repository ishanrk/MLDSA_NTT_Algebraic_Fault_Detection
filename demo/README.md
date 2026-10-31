# ML-DSA-44 NTT fault demonstration

This extends the original `ishanrk/MLDSA_NTT_Algebraic_Fault_Detection` source. The ordinary implementation and both existing checkers remain available. The new checker is selected with `MLDSA_ENCODED_CHECKER`. The simulated fault hook and alternate signing path are compiled only in the local demo targets.

## Run locally

Requires macOS or Linux, Python 3, `make`, and a C11 compiler. The checker demo obtains random bytes with `arc4random_buf` on macOS and `getrandom` on Linux. OpenSSL 3.5 or newer optionally enables an independent signature verifier.

```sh
./RUN_DEMO.sh
make fault-demo
python3 demo/run_demo.py --trials 10 --json demo/results.json
python3 tools/audit_encoded.py --json demo/certificate.json
make demo/bin/benchmark
./demo/bin/benchmark
make test
```

Run either of the first two commands for the one trial presentation. If macOS removes executable permission after download, use `bash RUN_DEMO.sh`.

`make fault-demo` creates a disposable key, runs both attacks, recovers the secret component, constructs an equivalent key, signs a message the victim never signed, and checks the protected signer. It deletes keys on exit. Neither [results.json](results.json) nor [certificate.json](certificate.json) contains secret keys.

Successful output for each attack includes `recovered s1: 1024/1024`, `distinct new message forgery: VERIFY_OK`, and `protected signer: SIGN_ABORT, no signature file`.

| Path | Fault target | Attacker input | Faulted signature |
| --- | --- | --- | --- |
| Deterministic | Challenge NTT, all twiddles zero | Paired signatures with the same nonce and (c_0=0) | Invalid |
| Randomized | Four first attempt nonce NTTs, all twiddles zero | One released faulty signature from the optional NTT domain (z) signer | Valid |

The deterministic path uses `rnd=0`. It seeks a message where the clean and faulted attempts both accept at the first rejection check. Then (z=y+c s_1), (z^*=y), and (s_1=c^{-1}(z-z^*)). The randomized path requires `MLDSA_NTT_DOMAIN_Z`, where (z=T^{-1}(T(y)+T(c)\circ T(s_1))). The ordinary `z=y+c s1` implementation does not have that specific nonce NTT leak. The runner verifies byte identical clean signatures from both paths under the same seed.

These are simulated arithmetic effects of Ravi et al.'s twiddle pointer corruption, adapted to ML-DSA-44. They are not physical injections. Four NTT calls are explicitly selected in software for the randomized case. This does not show that a single physical pulse affects all four calls here.

## Checker and certificate

The forward NTT (T) receives five fresh field elements (r) and fixed public matrices (U,W,H,V), with (H=WT^{-1}) and (V=TU). The code computes (b=\operatorname{NTT}(a+Ur)), removes (Vr), and releases (y=b-Vr) only if the six equations (Hy=Wa) hold. Failure clears the NTT output and aborts signing before writing a signature. Four fixed nonce inputs share one mask in the protected signer. Other calls use a fresh mask.

The [audit](../tools/audit_encoded.py) verifies the exact generated tables and these field model claims:

1. Every harmful one or two arbitrary additive errors among 2,304 modeled boundary wires is detected. Every harmful error in one contiguous interval of at most six words at one boundary is detected.
2. For every longer contiguous interval at all nine boundaries, zeroization, nontrivial common scaling, or one common overwrite value has escape probability at most (q^{-5}) for a fixed input.
3. Zeroing every twiddle in one forward NTT has escape probability at most (q^{-5}).

There are 282,375 longer intervals for each of the scaling and overwrite classes. Including the full zero twiddle event, an attacker who sees the public mask and then chooses one covered event has union bound (564751/q^5\approx1.37\cdot10^{-29}) per NTT. If any of four masked nonce NTTs can be targeted, multiply by four. These are counts of algebraic fault templates, not physical injections or a measured fraction of physical faults.

## Cost and boundaries

`demo/bench_encoded.c` times this C source against its original NTT on the current host. Run it on the presentation laptop. The [five run host record](benchmark_host.txt) shows 146.4 percent added time for one transform and 98.9 percent added time per transform in a four input batch. We have no measured speed advantage over full recomputation and no Cortex M4 timing for this new checker. The earlier prototype's 75 percent batch estimate is from different code and is not a measurement for this package.

The proof assumes one event from the stated catalog, correct field arithmetic, a fixed original input before sampling fresh (r), intact input anchoring, and an intact checker and abort path. Arbitrary fault combinations, pre-encoding faults, checker faults, out of range machine faults that cause overflow, inverse NTT faults, and ineffective fault leakage are not covered. Novelty against published schemes remains unestablished. Repeated attempts must count each fresh mask.

The attack source is Ravi et al., *Fiddling the Twiddle Constants*, TCHES 2023, section 5.1: https://eprint.iacr.org/2022/824.pdf. See [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md) for the proof, file map, and presentation notes.
