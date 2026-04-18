#!/usr/bin/env python3
import ctypes as C
import hashlib
import json
import sys
from pathlib import Path


class Shake(C.Structure):
    _fields_ = [("a", C.c_uint64 * 25), ("rate", C.c_size_t),
                ("pos", C.c_size_t), ("squeezing", C.c_int)]


def main():
    lib = C.CDLL(str(Path(sys.argv[1]).resolve()))
    root = Path(sys.argv[2])
    lib.mldsa_shake_init.argtypes = [C.POINTER(Shake), C.c_uint]
    lib.mldsa_shake_absorb.argtypes = [C.POINTER(Shake), C.c_void_p, C.c_size_t]
    lib.mldsa_shake_squeeze.argtypes = [C.POINTER(Shake), C.c_void_p, C.c_size_t]

    for strength in (128, 256):
        f = getattr(lib, f"mldsa_shake{strength}")
        f.argtypes = [C.c_void_p, C.c_size_t, C.c_void_p, C.c_size_t]
        path = root / f"SHAKE-{strength}-FIPS202"
        p = json.loads((path / "prompt.json").read_text())
        a = json.loads((path / "expectedResults.json").read_text())
        answers = {x["tcId"]: x["md"] for g in a["testGroups"] for x in g["tests"]}
        count = 0
        for g in p["testGroups"]:
            for t in g["tests"]:
                if t["len"] % 8 or t["outLen"] % 8:
                    continue
                msg = bytes.fromhex(t["msg"])[:t["len"] // 8]
                out = C.create_string_buffer(t["outLen"] // 8)
                f(out, len(out), msg, len(msg))
                assert out.raw.hex().lower() == answers[t["tcId"]].lower(), t["tcId"]
                count += 1

        rate = 168 if strength == 128 else 136
        for n in (0, 1, 3, rate - 1, rate, rate + 1, 2 * rate + 7):
            msg = bytes(i % 251 for i in range(n))
            for outlen in (1, 32, rate - 1, rate, rate + 1, 2 * rate + 9):
                want = getattr(hashlib, f"shake_{strength}")(msg).digest(outlen)
                out = C.create_string_buffer(outlen)
                f(out, outlen, msg, n)
                assert out.raw == want, (strength, n, outlen)

                s = Shake()
                lib.mldsa_shake_init(C.byref(s), strength)
                for part in (msg[:1], msg[1:rate], msg[rate:]):
                    lib.mldsa_shake_absorb(C.byref(s), part, len(part))
                got = C.create_string_buffer(outlen)
                off = 0
                for size in (1, (outlen - 1) // 2, outlen - 1 - (outlen - 1) // 2):
                    lib.mldsa_shake_squeeze(C.byref(s), C.byref(got, off), size)
                    off += size
                assert got.raw == want, (strength, n, outlen, "stream")
        print(f"SHAKE{strength}: {count} NIST ACVP vectors and 42 boundary cases passed")


if __name__ == "__main__":
    main()
