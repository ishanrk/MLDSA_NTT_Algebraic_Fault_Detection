#!/usr/bin/env python3
import ctypes as C
import json
import sys
from pathlib import Path


def main():
    lib = C.CDLL(str(Path(sys.argv[1]).resolve()))
    lib.mldsa44_sign.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t,
                                 C.c_void_p, C.c_size_t, C.c_void_p,
                                 C.c_size_t, C.c_void_p]
    lib.mldsa44_sign.restype = C.c_int
    root = Path(sys.argv[2]) / "ML-DSA-sigGen-FIPS204"
    p = json.loads((root / "prompt.json").read_text())
    a = json.loads((root / "expectedResults.json").read_text())
    answers = {x["tcId"]: x["signature"] for g in a["testGroups"] for x in g["tests"]}
    count = 0
    for g in p["testGroups"]:
        if g.get("parameterSet") != "ML-DSA-44" or g.get("signatureInterface") != "external" or g.get("preHash") != "pure":
            continue
        for t in g["tests"]:
            sk = bytes.fromhex(t["sk"])
            msg = bytes.fromhex(t["message"])
            ctx = bytes.fromhex(t["context"])
            rnd = bytes.fromhex(t["rnd"]) if "rnd" in t else bytes(32)
            sig = C.create_string_buffer(2420)
            rc = lib.mldsa44_sign(sig, sk, len(sk), msg, len(msg), ctx, len(ctx), rnd)
            assert rc == 0, (t["tcId"], "status")
            assert sig.raw.hex().lower() == answers[t["tcId"]].lower(), t["tcId"]
            count += 1
    print(f"NIST ACVP ML DSA 44 sigGen passed: {count} pure external cases")


if __name__ == "__main__":
    main()
