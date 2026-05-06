#!/usr/bin/env python3
import ctypes as C
import json
import sys
from pathlib import Path


def main():
    lib = C.CDLL(str(Path(sys.argv[1]).resolve()))
    lib.mldsa44_keygen.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p]
    root = Path(sys.argv[2]) / "ML-DSA-keyGen-FIPS204"
    p = json.loads((root / "prompt.json").read_text())
    a = json.loads((root / "expectedResults.json").read_text())
    answers = {x["tcId"]: x for g in a["testGroups"] for x in g["tests"]}
    count = 0
    for g in p["testGroups"]:
        if g["parameterSet"] != "ML-DSA-44":
            continue
        for t in g["tests"]:
            pk, sk = C.create_string_buffer(1312), C.create_string_buffer(2560)
            lib.mldsa44_keygen(pk, sk, bytes.fromhex(t["seed"]))
            want = answers[t["tcId"]]
            assert pk.raw.hex().lower() == want["pk"].lower(), (t["tcId"], "pk")
            assert sk.raw.hex().lower() == want["sk"].lower(), (t["tcId"], "sk")
            count += 1
    print(f"NIST ACVP ML DSA 44 keyGen passed: {count} cases")


if __name__ == "__main__":
    main()
