#!/usr/bin/env python3
"""build a signing key from recovered s1 and the original public key"""

import hashlib
import os

Q = 8380417
N = 256
ZETA = 1753
D = 13
POLY_COUNT = 4




# value is a coefficient modulo q
# return its signed form near zero
def centered(value):
    """center one modular coefficient"""
    return value if value <= Q // 2 else value - Q




# blob holds one packed polynomial
# bits is the width of each coefficient field
# top and signed select the small coefficient encoding
def decode_bits(blob, bits, top=0, signed=False):
    """unpack 256 coefficients"""
    packed = int.from_bytes(blob, "little")
    mask = (1 << bits) - 1
    values = [(packed >> (i * bits)) & mask for i in range(N)]
    return [(top - value) % Q for value in values] if signed else values




# values holds one polynomial of 256 coefficients
# bits is the width of each packed field
# top and signed select the small coefficient encoding
def encode_bits(values, bits, top=0, signed=False):
    """pack 256 coefficients"""
    digits = [top - centered(value) if signed else value for value in values]
    if len(digits) != N or any(not 0 <= value < 1 << bits for value in digits):
        raise ValueError("coefficient does not fit its packed field")


    packed = sum(value << (i * bits) for i, value in enumerate(digits))
    return packed.to_bytes(N * bits // 8, "little")




# value is an eight bit index
# return it with its bits reversed
def rev8(value):
    return int(f"{value:08b}"[::-1], 2)




ROOTS = [pow(ZETA, 2 * rev8(index) + 1, Q) for index in range(N)]
INVROOTS = [pow(root, Q - 2, Q) for root in ROOTS]
NINV = pow(N, Q - 2, Q)
assert len(set(ROOTS)) == N and all(pow(root, N, Q) == Q - 1 for root in ROOTS)




# poly holds 256 coefficients
# return its value at each negacyclic root
def ntt(poly):
    """evaluate one polynomial"""
    return [
        sum(coefficient * pow(root, index, Q)
            for index, coefficient in enumerate(poly)) % Q
        for root in ROOTS
    ]




# values holds one evaluation per root
# return the 256 polynomial coefficients
def intt(values):
    """interpolate one polynomial"""
    coefficients = [0] * N


    for inverse_root, evaluation in zip(INVROOTS, values):
        root_power = 1
        for index in range(N):
            coefficients[index] = (coefficients[index] + evaluation * root_power) % Q
            root_power = root_power * inverse_root % Q


    # divide by the number of roots after adding their contributions
    return [coefficient * NINV % Q for coefficient in coefficients]




# rho seeds the public matrix sampler
# row and col choose one matrix polynomial
# return its 256 ntt coefficients
def sample_a(rho, row, col):
    """sample one public matrix polynomial"""
    # use column then row to match the c sampler
    stream = hashlib.shake_128(rho + bytes([col, row])).digest(4096)
    coefficients = []


    for offset in range(0, len(stream) - 2, 3):
        # keep a 23 bit candidate only if it is below q
        candidate = int.from_bytes(stream[offset:offset + 3], "little") & 0x7fffff
        if candidate < Q:
            coefficients.append(candidate)
            if len(coefficients) == N:
                return coefficients


    raise AssertionError("not enough SHAKE output")




# value is one coefficient modulo q
# return its public high part and signed low part
def power2round(value):
    """split one coefficient for the public key"""
    value %= Q
    low = value % (1 << D)
    if low > 1 << (D - 1):
        low -= 1 << D


    high = (value - low) // (1 << D)
    return high, low




# pk is the original 1312 byte public key
# s1 holds four recovered secret polynomials
# return an equivalent 2560 byte signing key
def reconstruct(pk, s1):
    """rebuild a key for the original public key"""
    assert len(pk) == 1312 and len(s1) == POLY_COUNT
    assert all(len(poly) == N for poly in s1)


    # rho and the high bits of t come from the public key
    rho = pk[:32]
    tr = hashlib.shake_256(pk).digest(64)
    t1 = [
        decode_bits(pk[32 + 320 * row:32 + 320 * (row + 1)], 10)
        for row in range(POLY_COUNT)
    ]
    s1_ntt = [ntt(poly) for poly in s1]


    s2 = []
    t0 = []
    for row in range(POLY_COUNT):
        # multiply one public matrix row by all four s1 polynomials
        t_ntt = [0] * N
        for col in range(POLY_COUNT):
            matrix_poly = sample_a(rho, row, col)
            for index in range(N):
                t_ntt[index] = (
                    t_ntt[index] + matrix_poly[index] * s1_ntt[col][index]
                ) % Q
        t = intt(t_ntt)


        # the public key gives only high bits so try all five small s2 values
        # keep its low part in t0 for the signing key
        s2_row = []
        t0_row = []
        for index, coefficient in enumerate(t):
            for candidate in (0, 1, -1, 2, -2):
                high, low = power2round(coefficient + candidate)
                if high == t1[row][index]:
                    s2_row.append(candidate % Q)
                    t0_row.append(low % Q)
                    break
            else:
                raise AssertionError(
                    f"no s2 candidate found: {row, index, coefficient, t1[row][index]}"
                )
        s2.append(s2_row)
        t0.append(t0_row)


    # choose a fresh nonce key so this secret differs from the original
    nonce_key = os.urandom(32)


    # pack rho nonce key tr s1 s2 and t0 in secret key order
    secret = bytearray(rho + nonce_key + tr)
    secret.extend(b"".join(encode_bits(poly, 3, 2, True) for poly in s1))
    secret.extend(b"".join(encode_bits(poly, 3, 2, True) for poly in s2))
    secret.extend(b"".join(encode_bits(poly, 13, 4096, True) for poly in t0))

    assert len(secret) == 2560
    return bytes(secret)
