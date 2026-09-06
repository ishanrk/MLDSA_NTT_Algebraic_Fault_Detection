#!/usr/bin/env python3
import ctypes as C
import json
import sys
from pathlib import Path


def data(root, name):
    path = root / name
    p = json.loads((path / 'prompt.json').read_text())
    a = json.loads((path / 'expectedResults.json').read_text())
    answers = {t['tcId']: t for g in a['testGroups'] for t in g['tests']}
    return p['testGroups'], answers


def main():
    lib = C.CDLL(str(Path(sys.argv[1]).resolve()))
    root = Path(sys.argv[2])
    lib.mldsa44_keygen.argtypes = [C.c_void_p] * 3
    lib.mldsa44_keygen.restype = C.c_int
    lib.mldsa44_sign.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t,
                                 C.c_void_p, C.c_size_t, C.c_void_p,
                                 C.c_size_t, C.c_void_p]
    lib.mldsa44_sign.restype = C.c_int
    lib.mldsa44_verify.argtypes = [C.c_void_p, C.c_size_t, C.c_void_p,
                                   C.c_size_t, C.c_void_p, C.c_size_t,
                                   C.c_void_p, C.c_size_t]
    lib.mldsa44_verify.restype = C.c_int
    groups, answers = data(root, 'ML-DSA-keyGen-FIPS204')
    t = next(t for g in groups if g['parameterSet'] == 'ML-DSA-44' for t in g['tests'])
    pk, sk = C.create_string_buffer(1312), C.create_string_buffer(2560)
    assert lib.mldsa44_keygen(pk, sk, bytes.fromhex(t['seed'])) == 0
    assert pk.raw == bytes.fromhex(answers[t['tcId']]['pk'])
    assert sk.raw == bytes.fromhex(answers[t['tcId']]['sk'])
    print(f"NIST keyGen tcId {t['tcId']} PASS")

    groups, answers = data(root, 'ML-DSA-sigGen-FIPS204')
    t = next(t for g in groups if g['parameterSet'] == 'ML-DSA-44'
             and g.get('signatureInterface') == 'external' and g.get('preHash') == 'pure'
             for t in g['tests'])
    sk = bytes.fromhex(t['sk'])
    msg, ctx = bytes.fromhex(t['message']), bytes.fromhex(t['context'])
    rnd = bytes.fromhex(t['rnd']) if 'rnd' in t else bytes(32)
    sig = C.create_string_buffer(2420)
    assert lib.mldsa44_sign(sig, sk, len(sk), msg, len(msg), ctx, len(ctx), rnd) == 0
    assert sig.raw == bytes.fromhex(answers[t['tcId']]['signature'])
    print(f"NIST sigGen tcId {t['tcId']} PASS")

    groups, answers = data(root, 'ML-DSA-sigVer-FIPS204')
    cases = [t for g in groups if g['parameterSet'] == 'ML-DSA-44'
             and g.get('signatureInterface') == 'external' and g.get('preHash') == 'pure'
             for t in g['tests']]
    for valid in (True, False):
        t = next(t for t in cases if answers[t['tcId']]['testPassed'] == valid)
        pk, sig = bytes.fromhex(t['pk']), bytes.fromhex(t['signature'])
        msg, ctx = bytes.fromhex(t['message']), bytes.fromhex(t['context'])
        rc = lib.mldsa44_verify(pk, len(pk), msg, len(msg), ctx, len(ctx), sig, len(sig))
        assert (rc == 0) == valid
        print(f"NIST sigVer tcId {t['tcId']} expected {valid} PASS")


if __name__ == '__main__':
    main()
