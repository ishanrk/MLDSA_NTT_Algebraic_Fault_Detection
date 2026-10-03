#!/usr/bin/env python3
"""Generate keys, sign a file, or verify a file with the host ML-DSA-44 library."""

import argparse
import ctypes
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PK_BYTES, SK_BYTES, SIG_BYTES = 1312, 2560, 2420


def display_path(path):
    """Show a short path from the current directory when possible."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        return resolved


def input_file(path, size=None):
    data = path.read_bytes()
    if size is not None and len(data) != size:
        raise ValueError(f"{path}: expected {size} bytes, got {len(data)}")
    return data


def preview_bytes(label, data, path, private=False):
    """Print a byte preview and the location of an existing or new file."""
    print(f"{label} ({len(data)} bytes)")
    if not private:
        print(f"  first {min(32, len(data))}: {data[:32].hex(' ') or '(empty)'}")
    print(f"  full file: {display_path(path)}")


def show_bytes(label, data, path, private=False):
    """Save a byte string and show the location and short preview."""
    path.write_bytes(data)
    preview_bytes(label, data, path, private)


def show_pair(label, suffix, expected, actual, directory, private=False):
    print(f"\n{label.upper()}")
    show_bytes("Expected", expected, directory / f"expected.{suffix}", private)
    print()
    show_bytes("Actual", actual, directory / f"actual.{suffix}", private)


def run_vector(lib, kind, case_id):
    """Run one stored pure FIPS case and compare it with its expected result."""
    names = {"keygen": "keyGen", "siggen": "sigGen", "sigver": "sigVer"}
    name = names[kind]
    folder = ROOT / "vectors" / f"ML-DSA-{name}-FIPS204"
    groups = json.loads((folder / "test_vec.json").read_text())["testGroups"]
    answers = json.loads((folder / "expectedResults.json").read_text())
    answer = next((test for group in answers["testGroups"]
                   for test in group["tests"] if test["tcId"] == case_id), None)
    selected = next(((group, test) for group in groups for test in group["tests"]
                     if test["tcId"] == case_id), None)
    if selected is None or answer is None:
        raise SystemExit(f"No stored {name} case {case_id}")
    group, case = selected
    if group["parameterSet"] != "ML-DSA-44" or group.get("preHash", "pure") != "pure":
        raise SystemExit(f"{name} case {case_id} uses a mode this pure ML-DSA-44 API does not support")
    if kind != "keygen" and group.get("signatureInterface") != "external":
        raise SystemExit(f"{name} case {case_id} requires the external signature interface")

    directory = ROOT / "build" / "vector-results" / f"{kind}-{case_id}"
    directory.mkdir(parents=True, exist_ok=True)
    print(f"FIPS {name} case {case_id}\n")
    print("SOURCE VECTORS")
    print(f"  input: {display_path(folder / 'test_vec.json')}")
    print(f"  expected: {display_path(folder / 'expectedResults.json')}")

    if kind == "keygen":
        pk, sk = ctypes.create_string_buffer(PK_BYTES), ctypes.create_string_buffer(SK_BYTES)
        seed = bytes.fromhex(case["seed"])
        rc = lib.mldsa44_keygen(pk, sk, seed)
        expected_pk, expected_sk = bytes.fromhex(answer["pk"]), bytes.fromhex(answer["sk"])
        print("\nINPUT")
        show_bytes("Seed", seed, directory / "input.seed")
        show_pair("public key", "pk", expected_pk, pk.raw, directory)
        show_pair("secret key", "sk", expected_sk, sk.raw, directory, private=True)
        passed = rc == 0 and pk.raw == expected_pk and sk.raw == expected_sk
        detail = "exact public and secret keys"
    elif kind == "siggen":
        sk = bytes.fromhex(case["sk"])
        message = bytes.fromhex(case["message"])
        context = bytes.fromhex(case["context"])
        rnd = bytes.fromhex(case["rnd"]) if "rnd" in case else bytes(32)
        signature = ctypes.create_string_buffer(SIG_BYTES)
        rc = lib.mldsa44_sign(signature, sk, len(sk), message, len(message),
                              context or None, len(context), rnd)
        expected_sig = bytes.fromhex(answer["signature"])
        print("\nINPUTS")
        show_bytes("Secret key", sk, directory / "input.sk", private=True)
        (directory / "input.message").write_bytes(message)
        (directory / "input.context").write_bytes(context)
        (directory / "input.rnd").write_bytes(rnd)
        print()
        print(f"  message: {display_path(directory / 'input.message')}")
        print(f"  context: {display_path(directory / 'input.context')}")
        print(f"  randomness: {display_path(directory / 'input.rnd')}")
        show_pair("signature", "sig", expected_sig, signature.raw, directory)
        passed = rc == 0 and signature.raw == expected_sig
        detail = "exact signature"
    else:
        pk = bytes.fromhex(case["pk"])
        message = bytes.fromhex(case["message"])
        context = bytes.fromhex(case["context"])
        signature = bytes.fromhex(case["signature"])
        rc = lib.mldsa44_verify(pk, len(pk), message, len(message),
                                context or None, len(context), signature, len(signature))
        expected = answer["testPassed"]
        print("\nINPUTS")
        show_bytes("Public key", pk, directory / "input.pk")
        print()
        show_bytes("Signature", signature, directory / "input.sig")
        (directory / "input.message").write_bytes(message)
        (directory / "input.context").write_bytes(context)
        print()
        print(f"  message: {display_path(directory / 'input.message')}")
        print(f"  context: {display_path(directory / 'input.context')}")
        print("\nVERIFICATION")
        print(f"verification expected: {'accept' if expected else 'reject'}")
        print(f"verification actual: {'accept' if rc == 0 else 'reject'} (C return code {rc})")
        passed = (rc == 0) == expected
        detail = "expected accept" if expected else "expected reject"
    if not passed:
        raise SystemExit(f"\nFIPS {name} case {case_id}: FAIL\n")
    print(f"\nFIPS {name} case {case_id}: {detail} PASS")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    # just add multiple commands like keygen , siggen etc
    commands = parser.add_subparsers(dest="command", required=True)
    keygen = commands.add_parser("keygen", help="write a new public and secret key pair")
    keygen.add_argument("public_key", type=Path)
    keygen.add_argument("secret_key", type=Path)
    sign = commands.add_parser("sign", help="sign the bytes in a message file")
    sign.add_argument("secret_key", type=Path)
    sign.add_argument("message", type=Path)
    sign.add_argument("signature", type=Path)
    verify = commands.add_parser("verify", help="verify a signature against file bytes")
    verify.add_argument("public_key", type=Path)
    verify.add_argument("message", type=Path)
    verify.add_argument("signature", type=Path)

    # for each command ust ad the context file
    for command in (sign, verify):
        command.add_argument("--context-file", type=Path,
                             help="optional raw context bytes (at most 255)")
    vector = commands.add_parser("vector", help="check one stored pure FIPS 204 case")
    # just select the exact argument and which test ID you want to test again
    vector.add_argument("kind", choices=("keygen", "siggen", "sigver"))
    vector.add_argument("case", type=int, help="tcId within that vector kind")
    args = parser.parse_args()

    # build automatically, so there is no separate preparation command.
    subprocess.run(["make", "-s", "build/libmldsa_nttz.so"], cwd=ROOT, check=True)
    
    # jsut loads the library into python
    lib = ctypes.CDLL(str(ROOT / "build/libmldsa_nttz.so"))
    pointer, size = ctypes.c_void_p, ctypes.c_size_t

    # withou specifying types you can get errors
    lib.mldsa44_keygen.argtypes = [pointer, pointer, pointer]
    lib.mldsa44_sign.argtypes = [pointer, pointer, size, pointer, size,
                                 pointer, size, pointer]
    lib.mldsa44_verify.argtypes = [pointer, size, pointer, size,
                                   pointer, size, pointer, size]

    if args.command == "vector":
        run_vector(lib, args.kind, args.case)
        return

    if args.command == "keygen":
        pk, sk = ctypes.create_string_buffer(PK_BYTES), ctypes.create_string_buffer(SK_BYTES)
        if lib.mldsa44_keygen(pk, sk, os.urandom(32)):
            raise RuntimeError("key generation failed")
        print("KEYGEN\n")
        print("INPUT")
        print("  seed: 32 random bytes from the OS")
        print("\nOUTPUTS")
        show_bytes("Public key", pk.raw, args.public_key)
        print()
        show_bytes("Secret key", sk.raw, args.secret_key, private=True)
        args.secret_key.chmod(0o600)
        print(f"\nKEYGEN_OK: {display_path(args.public_key)}, {display_path(args.secret_key)}\n")
        return

    message = input_file(args.message)
    context = input_file(args.context_file) if args.context_file else b""
    if len(context) > 255:
        raise ValueError("context must be at most 255 bytes")
    if args.command == "sign":
        secret = input_file(args.secret_key, SK_BYTES)
        print("SIGN\n")
        print("INPUTS")
        preview_bytes("Secret key", secret, args.secret_key, private=True)
        print()
        preview_bytes("Message", message, args.message)
        print()
        if args.context_file:
            preview_bytes("Context", context, args.context_file)
        else:
            print("Context (0 bytes)\n  none")
        signature = ctypes.create_string_buffer(SIG_BYTES)
        if lib.mldsa44_sign(signature, secret, len(secret), message, len(message),
                            context or None, len(context), os.urandom(32)):
            raise RuntimeError("signing failed")
        print("\nOUTPUT")
        show_bytes("Signature", signature.raw, args.signature)
        print(f"\nSIGN_OK: {display_path(args.signature)}\n")
    else:
        public = input_file(args.public_key, PK_BYTES)
        signature = input_file(args.signature, SIG_BYTES)
        print("VERIFY\n")
        print("INPUTS")
        preview_bytes("Public key", public, args.public_key)
        print()
        preview_bytes("Message", message, args.message)
        print()
        if args.context_file:
            preview_bytes("Context", context, args.context_file)
        else:
            print("Context (0 bytes)\n  none")
        print()
        preview_bytes("Signature", signature, args.signature)
        print("\nRESULT")
        if lib.mldsa44_verify(public, len(public), message, len(message),
                              context or None, len(context), signature, len(signature)):
            print("VERIFY_FAIL\n")
            raise SystemExit(1)
        print("VERIFY_OK\n")


if __name__ == "__main__":
    main()
