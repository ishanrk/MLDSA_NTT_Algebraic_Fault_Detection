"""Attacker-side recovery from ONE randomized, faulted ML-DSA-44 signature.

Only the public signature is used here. The victim's secret key, random seed,
nonce, and clean signature are never inputs to recover_s1().
"""
import hashlib

from derive_equivalent import N, Q, centered, decode_bits, intt, ntt

TAU = 39
ETA = 2
GAMMA1 = 131072


def challenge_from_seed(ctilde):
    stream = hashlib.shake_256(ctilde).digest(3072)
    signs = stream[:8]
    cursor = 8
    coeff = [0] * N
    for i in range(N - TAU, N):
        while True:
            j = stream[cursor]
            cursor += 1
            if j <= i:
                break
        coeff[i] = coeff[j]
        coeff[j] = Q - 1 if (signs[(i - (N - TAU)) // 8] >> ((i - (N - TAU)) % 8)) & 1 else 1
    assert sum(v != 0 for v in coeff) == TAU
    return coeff


def parse_signature(sig):
    if len(sig) != 2420:
        raise ValueError("expected a complete ML-DSA-44 signature")
    ctilde = sig[:32]
    z = [decode_bits(sig[32 + 576*i:32 + 576*(i+1)], 18, GAMMA1, True)
         for i in range(4)]
    return challenge_from_seed(ctilde), z


def recover_s1(sig):
    challenge, z = parse_signature(sig)
    c_hat = ntt(challenge)
    if 0 in c_hat:
        raise ValueError("challenge not invertible in the polynomial ring")
    inverse_hat = [pow(v, Q - 2, Q) for v in c_hat]
    # u = c^(-1) * X^0. Every candidate differs from the base by d*u,
    # where d is the unknown constant coefficient of c*s1.
    u = intt(inverse_hat)
    recovered = []
    guesses = []
    for row in z:
        known = row.copy()
        known[0] = 0
        base_hat = ntt(known)
        base = intt([a*b % Q for a,b in zip(base_hat,inverse_hat)])
        candidates = []
        for d in range(-TAU*ETA, TAU*ETA + 1):
            s = [(a + d*b) % Q for a,b in zip(base,u)]
            if all(abs(centered(v)) <= ETA for v in s):
                candidates.append((d,s))
        if len(candidates) != 1:
            raise ValueError(f"secret candidate ambiguity: {len(candidates)}")
        d,s = candidates[0]
        recovered.append(s)
        guesses.append(d)
    return recovered, guesses
