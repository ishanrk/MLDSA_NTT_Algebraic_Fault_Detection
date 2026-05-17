#!/usr/bin/env python3
import ctypes as C
import json
import sys
from pathlib import Path


def main():
    lib = C.CDLL(str(Path(sys.argv[1]).resolve()))
    lib.mldsa44_verify.argtypes = [C.c_void_p, C.c_size_t, C.c_void_p,
                                   C.c_size_t, C.c_void_p, C.c_size_t,
                                   C.c_void_p, C.c_size_t]
    lib.mldsa44_verify.restype = C.c_int
    root = Path(sys.argv[2]) / "ML-DSA-sigVer-FIPS204"
    p = json.loads((root / "prompt.json").read_text())
    a = json.loads((root / "expectedResults.json").read_text())
    answers = {x["tcId"]: x["testPassed"] for g in a["testGroups"] for x in g["tests"]}
    count = valid = 0
    for g in p["testGroups"]:
        if g.get("parameterSet") != "ML-DSA-44" or g.get("signatureInterface") != "external" or g.get("preHash") != "pure":
            continue
        for t in g["tests"]:
            pk = bytes.fromhex(t["pk"])
            msg = bytes.fromhex(t["message"])
            ctx = bytes.fromhex(t["context"])
            sig = bytes.fromhex(t["signature"])
            rc = lib.mldsa44_verify(pk, len(pk), msg, len(msg), ctx, len(ctx), sig, len(sig))
            assert (rc == 0) == answers[t["tcId"]], (t["tcId"], rc)
            count += 1
            valid += rc == 0
    print(f"NIST ACVP ML DSA 44 sigVer passed: {count} pure external cases ({valid} valid)")


if __name__ == "__main__":
    main()
