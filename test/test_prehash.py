#!/usr/bin/env python3
import ctypes as C
import hashlib
import json
import sys
from pathlib import Path


HASHES = {
    "SHA2-256": (1, "sha256", 32),
    "SHA2-384": (2, "sha384", 48),
    "SHA2-512": (3, "sha512", 64),
    "SHA2-224": (4, "sha224", 28),
    "SHA2-512/224": (5, "sha512_224", 28),
    "SHA2-512/256": (6, "sha512_256", 32),
    "SHA3-224": (7, "sha3_224", 28),
    "SHA3-256": (8, "sha3_256", 32),
    "SHA3-384": (9, "sha3_384", 48),
    "SHA3-512": (10, "sha3_512", 64),
    "SHAKE-128": (11, "shake_128", 32),
    "SHAKE-256": (12, "shake_256", 64),
}


def digest(name, msg):
    ident, alg, size = HASHES[name]
    h = hashlib.new(alg, msg)
    return ident, h.digest(size) if alg.startswith("shake") else h.digest()


def main():
    lib = C.CDLL(str(Path(sys.argv[1]).resolve()))
    lib.mldsa44_sign_digest.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t,
                                        C.c_uint, C.c_void_p, C.c_size_t,
                                        C.c_void_p, C.c_size_t, C.c_void_p]
    lib.mldsa44_sign_digest.restype = C.c_int
    lib.mldsa44_verify_digest.argtypes = [C.c_void_p, C.c_size_t, C.c_uint,
                                          C.c_void_p, C.c_size_t, C.c_void_p,
                                          C.c_size_t, C.c_void_p, C.c_size_t]
    lib.mldsa44_verify_digest.restype = C.c_int
    root = Path(sys.argv[2])
    p = json.loads((root / "ML-DSA-sigGen-FIPS204/prompt.json").read_text())
    a = json.loads((root / "ML-DSA-sigGen-FIPS204/expectedResults.json").read_text())
    answers = {x["tcId"]: x["signature"] for g in a["testGroups"] for x in g["tests"]}
    signs = 0
    for g in p["testGroups"]:
        if g.get("parameterSet") != "ML-DSA-44" or g.get("signatureInterface") != "external" or g.get("preHash") != "preHash":
            continue
        for t in g["tests"]:
            ident, d = digest(t["hashAlg"], bytes.fromhex(t["message"]))
            sk = bytes.fromhex(t["sk"])
            ctx = bytes.fromhex(t["context"])
            rnd = bytes.fromhex(t["rnd"]) if "rnd" in t else bytes(32)
            sig = C.create_string_buffer(2420)
            rc = lib.mldsa44_sign_digest(sig, sk, len(sk), ident, d, len(d), ctx, len(ctx), rnd)
            assert rc == 0, (t["tcId"], "status")
            assert sig.raw.hex().lower() == answers[t["tcId"]].lower(), t["tcId"]
            signs += 1

    p = json.loads((root / "ML-DSA-sigVer-FIPS204/prompt.json").read_text())
    a = json.loads((root / "ML-DSA-sigVer-FIPS204/expectedResults.json").read_text())
    answers = {x["tcId"]: x["testPassed"] for g in a["testGroups"] for x in g["tests"]}
    verifies = valid = 0
    for g in p["testGroups"]:
        if g.get("parameterSet") != "ML-DSA-44" or g.get("signatureInterface") != "external" or g.get("preHash") != "preHash":
            continue
        for t in g["tests"]:
            ident, d = digest(t["hashAlg"], bytes.fromhex(t["message"]))
            pk = bytes.fromhex(t["pk"])
            ctx = bytes.fromhex(t["context"])
            sig = bytes.fromhex(t["signature"])
            rc = lib.mldsa44_verify_digest(pk, len(pk), ident, d, len(d), ctx, len(ctx), sig, len(sig))
            assert (rc == 0) == answers[t["tcId"]], (t["tcId"], rc)
            verifies += 1
            valid += rc == 0
    print(f"NIST ACVP HashML DSA 44 passed: {signs} sign, {verifies} verify ({valid} valid)")


if __name__ == "__main__":
    main()
