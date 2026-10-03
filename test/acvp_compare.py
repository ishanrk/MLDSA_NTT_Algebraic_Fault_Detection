#!/usr/bin/env python3
"""compare plain, memory saving, and protected mldsa44 with nist vectors."""

import argparse
import ctypes as c
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PK_BYTES = 1312
SK_BYTES = 2560
SIG_BYTES = 2420


def checked_data(root, group):
    test_vectors = json.loads((root / group / "test_vec.json").read_text())
    expected_results = json.loads((root / group / "expectedResults.json").read_text())
    answers = {test["tcId"]: test for g in expected_results["testGroups"]
               for test in g["tests"]}
    return test_vectors["testGroups"], answers


def load_library(path):
    lib = c.CDLL(str(path.resolve()))
    lib.mldsa44_keygen.argtypes = (c.c_void_p,) * 3
    lib.mldsa44_keygen.restype = c.c_int
    lib.mldsa44_sign.argtypes = (c.c_void_p, c.c_void_p, c.c_size_t,
                                 c.c_void_p, c.c_size_t, c.c_void_p,
                                 c.c_size_t, c.c_void_p)
    lib.mldsa44_sign.restype = c.c_int
    lib.mldsa44_verify.argtypes = (c.c_void_p, c.c_size_t, c.c_void_p,
                                   c.c_size_t, c.c_void_p, c.c_size_t,
                                   c.c_void_p, c.c_size_t)
    lib.mldsa44_verify.restype = c.c_int
    return lib


def group_cases(groups, pure_external=False, require_rnd=False):
    for group in groups:
        if group.get("parameterSet") != "ML-DSA-44":
            continue
        if pure_external and (group.get("signatureInterface") != "external" or
                              group.get("preHash") != "pure"):
            continue
        for test in group["tests"]:
            if require_rnd and "rnd" not in test:
                continue
            yield test


def select(cases, ids):
    cases = list(cases)
    if ids is None:
        return cases
    index = {t["tcId"]: t for t in cases}
    unknown = set(ids) - index.keys()
    if unknown:
        raise ValueError(f"No matching ML-DSA-44 case ID: {sorted(unknown)}")
    return [index[n] for n in ids]


def run(root, libraries, key_ids, sig_ids, ver_ids, show_inputs):
    versions = [(path.name, load_library(path)) for path in libraries]
    stats = {name: {"keyGen": 0, "sigGen": 0, "sigVer": 0}
             for name, _ in versions}
    keys, key_answers = checked_data(root, "ML-DSA-keyGen-FIPS204")
    signatures, sign_answers = checked_data(root, "ML-DSA-sigGen-FIPS204")
    verifications, verify_answers = checked_data(root, "ML-DSA-sigVer-FIPS204")

    for case in select(group_cases(keys), key_ids):
        seed = bytes.fromhex(case["seed"])
        expected_pk = bytes.fromhex(key_answers[case["tcId"]]["pk"])
        expected_sk = bytes.fromhex(key_answers[case["tcId"]]["sk"])
        if show_inputs:
            print(f"keyGen tcId={case['tcId']} seed={seed.hex()}")
        for name, lib in versions:
            pk, sk = c.create_string_buffer(PK_BYTES), c.create_string_buffer(SK_BYTES)
            if lib.mldsa44_keygen(pk, sk, seed) != 0:
                raise AssertionError(f"{name}: keyGen {case['tcId']} returned error")
            if pk.raw != expected_pk or sk.raw != expected_sk:
                raise AssertionError(f"{name}: keyGen {case['tcId']} differs from NIST")
            stats[name]["keyGen"] += 1
        print(f"keyGen tcId={case['tcId']} expected pk/sk exact bytes PASS: {len(versions)} builds")

    for case in select(group_cases(signatures, pure_external=True), sig_ids):
        sk = bytes.fromhex(case["sk"])
        msg = bytes.fromhex(case["message"])
        ctx = bytes.fromhex(case["context"])
        rnd = bytes.fromhex(case["rnd"]) if "rnd" in case else bytes(32)
        expected = bytes.fromhex(sign_answers[case["tcId"]]["signature"])
        if show_inputs:
            print(f"sigGen tcId={case['tcId']} message={msg.hex()} context={ctx.hex()} rnd={rnd.hex()}")
        for name, lib in versions:
            sig = c.create_string_buffer(SIG_BYTES)
            rc = lib.mldsa44_sign(sig, sk, len(sk), msg, len(msg), ctx, len(ctx), rnd)
            if rc != 0 or sig.raw != expected:
                raise AssertionError(f"{name}: sigGen {case['tcId']} differs from NIST, rc={rc}")
            stats[name]["sigGen"] += 1
        print(f"sigGen tcId={case['tcId']} randomized={'rnd' in case} message_bytes={len(msg)} exact bytes PASS: {len(versions)} builds")

    for case in select(group_cases(verifications, pure_external=True), ver_ids):
        pk = bytes.fromhex(case["pk"])
        msg = bytes.fromhex(case["message"])
        ctx = bytes.fromhex(case["context"])
        sig = bytes.fromhex(case["signature"])
        expected = verify_answers[case["tcId"]]["testPassed"]
        if show_inputs:
            print(f"sigVer tcId={case['tcId']} message={msg.hex()} context={ctx.hex()} signature_bytes={len(sig)}")
        for name, lib in versions:
            rc = lib.mldsa44_verify(pk, len(pk), msg, len(msg), ctx, len(ctx), sig, len(sig))
            if (rc == 0) != expected:
                raise AssertionError(f"{name}: sigVer {case['tcId']} expected {expected}, rc={rc}")
            stats[name]["sigVer"] += 1
        print(f"sigVer tcId={case['tcId']} expected={'accept' if expected else 'reject'} PASS: {len(versions)} builds")

    for name, counts in stats.items():
        print(f"{name}: keyGen={counts['keyGen']} sigGen={counts['sigGen']} sigVer={counts['sigVer']} PASS")


def ids(value):
    return [int(s) for s in value.split(",")]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("libraries", type=Path, nargs=3, metavar="LIBRARY")
    p.add_argument("--key-ids", type=ids)
    p.add_argument("--sig-ids", type=ids)
    p.add_argument("--ver-ids", type=ids)
    p.add_argument("--show-inputs", action="store_true")
    args = p.parse_args()
    run(args.root, args.libraries, args.key_ids, args.sig_ids,
        args.ver_ids, args.show_inputs)


if __name__ == "__main__":
    main()
