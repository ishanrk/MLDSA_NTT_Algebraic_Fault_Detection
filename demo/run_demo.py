#!/usr/bin/env python3
"""Run both simulated signing attacks and the encoded NTT defense locally."""
import argparse
import json
import os
import re
import secrets
import subprocess
import tempfile
from pathlib import Path

from attacker import parse_signature, recover_s1
from derive_equivalent import N, Q, centered, intt, ntt, reconstruct, sk_parse_original

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "demo/bin"
OPENSSL = None


def external_verify(pk, msg, sig):
    if OPENSSL is None:
        return "unavailable"
    p = subprocess.run([str(OPENSSL), "verify", str(pk), str(msg), str(sig)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise AssertionError(f"OpenSSL rejected a signature: {p.stdout} {p.stderr}")
    return "passed"


def optional_openssl():
    try:
        p = subprocess.run(["openssl", "version"], capture_output=True, text=True, check=True)
        m = re.search(r"OpenSSL\s+(\d+)\.(\d+)", p.stdout)
        if not m or tuple(map(int, m.groups())) < (3, 5):
            return None
        exe = BIN / "openssl_mldsa"
        subprocess.run([os.environ.get("CC", "cc"), "-O2", "-std=c11", "-Wall", "-Wextra",
                        str(ROOT / "demo/openssl_mldsa.c"), "-lcrypto", "-o", str(exe)],
                       capture_output=True, text=True, check=True)
        return exe
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def invoke(exe, *args, expected=(0,)):
    cmd = [str(BIN / exe), *map(str, args)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode not in expected:
        raise RuntimeError(f"{exe} {args[0]} returned {p.returncode}:\n{p.stdout}{p.stderr}")
    return p


def trace(p):
    m = re.search(r"forward_ntts=(\d+) faulted_ntts=(\d+) zero_twiddles=(\d+)", p.stderr)
    if not m:
        raise AssertionError(f"missing NTT trace: {p.stderr}")
    return tuple(map(int, m.groups()))


def matched_deterministic(d, pk, sk, trial):
    rnd = d / "det-rnd.bin"
    rnd.write_bytes(bytes(32))
    clean = d / "det-clean.sig"
    faulty = d / "det-fault.sig"
    msg = d / "det-message.txt"
    for attempt in range(1, 4001):
        msg.write_bytes(f"Deterministic local test message {trial} {attempt}".encode())
        if clean.exists():
            clean.unlink()
        if faulty.exists():
            faulty.unlink()
        a = invoke("standard", "sign", sk, msg, clean, rnd, "none")
        if trace(a)[0] != 17:
            continue
        c_clean, _ = parse_signature(clean.read_bytes())
        if c_clean[0] != 0:
            continue
        b = invoke("standard", "sign", sk, msg, faulty, rnd, "challenge", expected=(0, 5))
        if b.returncode == 5:
            continue
        if trace(b) != (17, 1, 255):
            raise AssertionError(f"unexpected challenge hook: {trace(b)}")
        c, z = parse_signature(clean.read_bytes())
        c_fault, z_fault = parse_signature(faulty.read_bytes())
        if c != c_fault or c[0] != 0:
            raise AssertionError("paired attempts had different challenges")
        den = [(v - c[0]) % Q for v in ntt(c)]
        if 0 in den:
            continue
        inv = [pow(v, Q - 2, Q) for v in den]
        recovered = []
        for arow, brow in zip(z, z_fault):
            diff = [(x - y) % Q for x, y in zip(arow, brow)]
            s = intt([(v * w) % Q for v, w in zip(ntt(diff), inv)])
            if not all(abs(centered(v)) <= 2 for v in s):
                raise AssertionError("paired recovery exceeded the secret bound")
            recovered.append(s)
        # The corrupted signature need not verify. The new forgery must verify.
        invoke("standard", "verify", pk, msg, clean)
        external_verify(pk, msg, clean)
        faulty_verify = invoke("standard", "verify", pk, msg, faulty, expected=(1,))
        blocked = d / "det-blocked.sig"
        p = invoke("protected-standard", "sign", sk, msg, blocked, rnd, "challenge", expected=(4,))
        if blocked.exists() or trace(p) != (17, 1, 255):
            raise AssertionError("protected challenge signer released output")
        protected_clean = d / "det-protected.sig"
        invoke("protected-standard", "sign", sk, msg, protected_clean, rnd, "none")
        if clean.read_bytes() != protected_clean.read_bytes():
            raise AssertionError("clean encoded signer changed the signature")
        return recovered, {
            "model": "deterministic paired challenge NTT zero twiddles",
            "chosen_messages_until_paired_first_attempt": attempt,
            "faulted_signature_verifies": faulty_verify.returncode == 0,
            "faulted_ntts": 1,
            "zeroed_twiddle_groups": 255,
            "protected_abort_before_signature_release": True,
            "protected_clean_byte_identical": True,
        }
    raise RuntimeError("no matched first attempt in 4000 messages")


def randomized(d, pk, sk):
    msg = d / "rnd-message.txt"
    msg.write_bytes(b"Randomized local test message")
    parity = d / "parity-rnd.bin"
    parity.write_bytes(secrets.token_bytes(32))
    std = d / "standard.sig"
    alt = d / "alternative.sig"
    invoke("standard", "sign", sk, msg, std, parity, "none")
    invoke("ntt-z", "sign", sk, msg, alt, parity, "none")
    if std.read_bytes() != alt.read_bytes():
        raise AssertionError("unfaulted NTT domain z path differs from standard")
    invoke("protected-ntt-z", "sign", sk, msg, d / "protected-clean.sig", parity, "none")
    if std.read_bytes() != (d / "protected-clean.sig").read_bytes():
        raise AssertionError("protected NTT domain z changed the clean signature")
    faulty = d / "rnd-fault.sig"
    rnd = d / "rnd-seed.bin"
    for attempt in range(1, 101):
        rnd.write_bytes(secrets.token_bytes(32))
        p = invoke("ntt-z", "sign", sk, msg, faulty, rnd, "nonce", expected=(0, 5))
        if p.returncode == 0:
            break
    else:
        raise RuntimeError("no accepted first attempt in 100 randomized requests")
    if trace(p) != (17, 4, 1020):
        raise AssertionError(f"unexpected nonce hook: {trace(p)}")
    invoke("standard", "verify", pk, msg, faulty)
    external_verify(pk, msg, faulty)
    # The attacker receives one signature. No clean signature or nonce is passed.
    recovered, guesses = recover_s1(faulty.read_bytes())
    blocked = d / "rnd-blocked.sig"
    p = invoke("protected-ntt-z", "sign", sk, msg, blocked, rnd, "nonce", expected=(4,))
    if blocked.exists() or trace(p) != (13, 1, 255):
        raise AssertionError("protected nonce signer released output")
    return recovered, {
        "model": "randomized single signature nonce NTT zero twiddles",
        "randomized_requests_until_first_attempt": attempt,
        "faulted_signature_verifies": True,
        "unfaulted_alternative_byte_identical": True,
        "unknown_constant_guesses": guesses,
        "faulted_ntts": 4,
        "zeroed_twiddle_groups": 1020,
        "protected_abort_before_signature_release": True,
        "protected_clean_byte_identical": True,
    }


def demonstrate_forgery(d, pk, sk, recovered, label):
    original, _, _ = sk_parse_original(sk.read_bytes())
    correct = sum(a == b for ra, rb in zip(original, recovered) for a, b in zip(ra, rb))
    if correct != 4 * N:
        raise AssertionError(f"{label}: only {correct}/1024 secret coefficients recovered")
    equivalent, _, _, _ = reconstruct(pk.read_bytes(), recovered)
    if equivalent == sk.read_bytes():
        raise AssertionError("alternate signing key unexpectedly equals victim key")
    alt = d / f"{label}-equivalent-sk.bin"
    alt.write_bytes(equivalent)
    msg = d / f"{label}-never-signed.txt"
    msg.write_bytes(f"Never signed by the victim: {label}".encode())
    rnd = d / f"{label}-forge-rnd.bin"
    rnd.write_bytes(secrets.token_bytes(32))
    sig = d / f"{label}-forged.sig"
    invoke("standard", "sign", alt, msg, sig, rnd, "none")
    invoke("standard", "verify", pk, msg, sig)
    external = external_verify(pk, msg, sig)
    return correct, external


def run_trial(index):
    with tempfile.TemporaryDirectory(prefix="mldsa-encoded-demo-") as temp:
        d = Path(temp)
        seed = d / "key-seed.bin"
        seed.write_bytes(secrets.token_bytes(32))
        pk, sk = d / "public.bin", d / "victim-secret.bin"
        invoke("standard", "keygen", pk, sk, seed)
        det_s1, det = matched_deterministic(d, pk, sk, index)
        det["recovered_s1_coefficients"], det["openssl_forgery_verifier"] = (
            demonstrate_forgery(d, pk, sk, det_s1, "deterministic"))
        det["new_message_forgery_verified"] = True
        rnd_s1, rnd = randomized(d, pk, sk)
        rnd["recovered_s1_coefficients"], rnd["openssl_forgery_verifier"] = (
            demonstrate_forgery(d, pk, sk, rnd_s1, "randomized"))
        rnd["new_message_forgery_verified"] = True
        return {"trial": index, "deterministic": det, "randomized": rnd}


def main():
    global OPENSSL
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=1)
    p.add_argument("--json", type=Path)
    args = p.parse_args()
    if not 1 <= args.trials <= 20:
        p.error("trials must be between 1 and 20")
    subprocess.run(["make", "-C", str(ROOT), "demo/bin/standard", "demo/bin/ntt-z",
                    "demo/bin/protected-standard", "demo/bin/protected-ntt-z"], check=True,
                   capture_output=True)
    OPENSSL = optional_openssl()
    results = []
    for i in range(1, args.trials + 1):
        report = run_trial(i)
        results.append(report)
        for name in ("deterministic", "randomized"):
            item = report[name]
            print(f"{name.upper()}: zero twiddles in {item['faulted_ntts']} NTT(s)")
            print(f"  recovered s1: {item['recovered_s1_coefficients']}/1024")
            print("  distinct new message forgery: VERIFY_OK")
            print("  protected signer: SIGN_ABORT, no signature file")
    summary = {"scheme": "ML-DSA-44 local software simulation",
               "trials": results, "successes": len(results)}
    if args.json:
        args.json.write_text(json.dumps(summary, indent=2) + "\n")
    print("OpenSSL 3.5+ independent verifier:", "available" if OPENSSL else "unavailable")
    print(f"PASS: both attack paths blocked in {len(results)} trial(s)")


if __name__ == "__main__":
    main()
