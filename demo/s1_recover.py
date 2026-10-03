"""Recover s1 from one randomized faulty ML-DSA-44 signature.

Recovery uses only the public signature.
"""

import hashlib

from signature_forgery import N, Q, centered, decode_bits, intt, ntt

TAU = 39
ETA = 2
GAMMA1 = 131072
SIGNATURE_BYTES = 2420
Z_BYTES_PER_POLY = 576


def challenge_from_seed(ctilde):
    """implements sample_in_ball"""
    stream = hashlib.shake_256(ctilde).digest(3072)
    signs = stream[:8]
    cursor = 8
    coefficients = [0] * N

    for index in range(N - TAU, N):
        while True:
            position = stream[cursor]
            cursor += 1
            if position <= index:
                break

        # move the old coefficient before placing the next signed nonzero one.
        coefficients[index] = coefficients[position]
        sign_index = index - (N - TAU)
        sign_bit = (signs[sign_index // 8] >> (sign_index % 8)) & 1
        coefficients[position] = Q - 1 if sign_bit else 1

    assert sum(value != 0 for value in coefficients) == TAU
    return coefficients


def parse_signature(signature):
    """return the challenge and four z polynomials from a signature."""
    if len(signature) != SIGNATURE_BYTES:
        raise ValueError("expected a complete ML-DSA-44 signature")

    challenge = challenge_from_seed(signature[:32])
    z_polynomials = []
    for row in range(4):
        start = 32 + row * Z_BYTES_PER_POLY
        packed = signature[start:start + Z_BYTES_PER_POLY]
        z_polynomials.append(decode_bits(packed, 18, GAMMA1, True))
    return challenge, z_polynomials


def recover_s1(signature):
    """find the small s1 polynomial consistent with each faulty z row."""
    challenge, z_polynomials = parse_signature(signature)
    challenge_ntt = ntt(challenge)
    if 0 in challenge_ntt:
        raise ValueError("challenge not invertible in the polynomial ring")
    inverse_ntt = [pow(value, Q - 2, Q) for value in challenge_ntt]

    # The fault hides z[0]. Its possible values are bounded by TAU * ETA.
    # Multiplying by c^-1 maps each guess into a possible s1 polynomial.
    missing_coefficient_effect = intt(inverse_ntt)
    recovered = []
    guesses = []
    for z_row in z_polynomials:
        known_coefficients = z_row.copy()
        known_coefficients[0] = 0
        known_ntt = ntt(known_coefficients)
        base = intt([
            value * inverse % Q
            for value, inverse in zip(known_ntt, inverse_ntt)
        ])

        candidates = []
        for missing_coefficient in range(-TAU * ETA, TAU * ETA + 1):
            candidate_secret = [
                (value + missing_coefficient * effect) % Q
                for value, effect in zip(base, missing_coefficient_effect)
            ]
            if all(abs(centered(value)) <= ETA for value in candidate_secret):
                candidates.append((missing_coefficient, candidate_secret))

        if len(candidates) != 1:
            raise ValueError(f"secret candidate ambiguity: {len(candidates)}")
        missing_coefficient, secret = candidates[0]
        recovered.append(secret)
        guesses.append(missing_coefficient)
    return recovered, guesses
