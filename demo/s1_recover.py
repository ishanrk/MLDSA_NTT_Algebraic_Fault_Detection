"""recover s1 from one faulty ml dsa 44 signature

recovery uses only the public signature
"""

import hashlib

from signature_forgery import N, Q, centered, decode_bits, intt, ntt

TAU = 39
ETA = 2
GAMMA1 = 131072
SIGNATURE_BYTES = 2420
Z_BYTES_PER_POLY = 576




# ctilde is the first 32 bytes of the signature
# return the sparse challenge polynomial
def challenge_from_seed(ctilde):
    """sample the challenge from its seed"""
    stream = hashlib.shake_256(ctilde).digest(3072)

    # the first eight bytes give signs and later bytes choose positions
    signs = stream[:8]
    cursor = 8
    coefficients = [0] * N


    for index in range(N - TAU, N):
        while True:
            position = stream[cursor]
            cursor += 1
            if position <= index:
                break

        # move the old value before putting a new sign in this position
        coefficients[index] = coefficients[position]
        sign_index = index - (N - TAU)
        sign_bit = (signs[sign_index // 8] >> (sign_index % 8)) & 1
        coefficients[position] = Q - 1 if sign_bit else 1


    assert sum(value != 0 for value in coefficients) == TAU
    return coefficients




# signature is the full 2420 byte ml dsa 44 signature
# return its challenge and four z polynomials
def parse_signature(signature):
    """unpack the public attack inputs"""
    if len(signature) != SIGNATURE_BYTES:
        raise ValueError("expected a complete ML-DSA-44 signature")


    challenge = challenge_from_seed(signature[:32])
    z_polynomials = []

    for row in range(4):
        start = 32 + row * Z_BYTES_PER_POLY
        packed = signature[start:start + Z_BYTES_PER_POLY]
        z_polynomials.append(decode_bits(packed, 18, GAMMA1, True))


    return challenge, z_polynomials




# signature is the faulty signature released by the signer
# return four small secret polynomials and four missing values
def recover_s1(signature):
    """recover each small secret row"""
    challenge, z_polynomials = parse_signature(signature)

    challenge_ntt = ntt(challenge)
    if 0 in challenge_ntt:
        raise ValueError("challenge not invertible in the polynomial ring")


    # invert the challenge at every ntt root
    inverse_ntt = [pow(value, Q - 2, Q) for value in challenge_ntt]


    # dividing one at index zero by the challenge gives its effect on s1
    missing_coefficient_effect = intt(inverse_ntt)
    recovered = []
    guesses = []


    for z_row in z_polynomials:
        # ignore z at index zero because it also contains the unknown nonce
        known_coefficients = z_row.copy()
        known_coefficients[0] = 0

        known_ntt = ntt(known_coefficients)
        base = intt([
            value * inverse % Q
            for value, inverse in zip(known_ntt, inverse_ntt)
        ])


        # at most tau secret terms of size eta contribute at index zero
        # try every possible constant term of the challenge times s1
        candidates = []
        for missing_coefficient in range(-TAU * ETA, TAU * ETA + 1):
            candidate_secret = [
                (value + missing_coefficient * effect) % Q
                for value, effect in zip(base, missing_coefficient_effect)
            ]

            # every secret coefficient must stay between negative eta and eta
            if all(abs(centered(value)) <= ETA for value in candidate_secret):
                candidates.append((missing_coefficient, candidate_secret))


        # the small coefficient bound should leave exactly one candidate
        if len(candidates) != 1:
            raise ValueError(f"secret candidate ambiguity: {len(candidates)}")


        missing_coefficient, secret = candidates[0]
        recovered.append(secret)
        guesses.append(missing_coefficient)


    return recovered, guesses
