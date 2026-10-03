#!/usr/bin/env python3
"""generate keys and sign or verify files with the host mldsa44 library."""

import argparse
import ctypes
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PK_BYTES, SK_BYTES, SIG_BYTES = 1312, 2560, 2420




# path is the file to show in the terminal
# return a short path when it is under the current directory
def display_path(path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        return resolved




# path is the file to read
# size can require an exact byte count
def input_file(path, size=None):
    data = path.read_bytes()
    if size is not None and len(data) != size:
        raise ValueError(f"{path}: expected {size} bytes, got {len(data)}")
    return data




# label names the data and data holds the bytes to preview
# path points at the full file
# private hides the byte preview for secret material
def preview_bytes(label, data, path, private=False):
    print(f"{label} ({len(data)} bytes)")
    if not private:
        print(f"  first {min(32, len(data))}: {data[:32].hex(' ') or '(empty)'}")
    print(f"  full file: {display_path(path)}")




# label names the data and data is the byte string to save
# path is the output file and private hides secret previews
def show_bytes(label, data, path, private=False):
    path.write_bytes(data)
    preview_bytes(label, data, path, private)




# label names the comparison and suffix names the file extension
# expected and actual are the two byte strings to save
# directory is the output folder and private hides secret previews
def show_pair(label, suffix, expected, actual, directory, private=False):
    print(f"\n{label.upper()}")
    show_bytes("Expected", expected, directory / f"expected.{suffix}", private)
    print()
    show_bytes("Actual", actual, directory / f"actual.{suffix}", private)




# lib is the host signing library
# kind chooses the vector type and case_id chooses its test case
# compare the result with the stored fips answer
def run_vector(lib, kind, case_id):
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

    # keep every input and output file for this case in one directory
    directory = ROOT / "build" / "vector-results" / f"{kind}-{case_id}"
    directory.mkdir(parents=True, exist_ok=True)
    print(f"FIPS {name} case {case_id}\n")
    print("SOURCE VECTORS")
    print(f"  input: {display_path(folder / 'test_vec.json')}")
    print(f"  expected: {display_path(folder / 'expectedResults.json')}")

    if kind == "keygen":
        # the vector seed must reproduce the expected key pair
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
        # for case 191 these are the fixed inputs used by the fault demo
        sk = bytes.fromhex(case["sk"])
        message = bytes.fromhex(case["message"])
        context = bytes.fromhex(case["context"])
        rnd = bytes.fromhex(case["rnd"]) if "rnd" in case else bytes(32)

        signature = ctypes.create_string_buffer(SIG_BYTES)
        rc = lib.mldsa44_sign(signature, sk, len(sk), message, len(message),
                              context or None, len(context), rnd)
        expected_sig = bytes.fromhex(answer["signature"])

        # save the vector inputs to files for inspection
        print("\nINPUTS")
        show_bytes("Secret key", sk, directory / "input.sk", private=True)
        (directory / "input.message").write_bytes(message)
        (directory / "input.context").write_bytes(context)
        (directory / "input.rnd").write_bytes(rnd)

        print()
        print(f"  message: {display_path(directory / 'input.message')}")
        print(f"  context: {display_path(directory / 'input.context')}")
        print(f"  randomness: {display_path(directory / 'input.rnd')}")

        # expected.sig is the fips answer and actual.sig is our output
        show_pair("signature", "sig", expected_sig, signature.raw, directory)

        passed = rc == 0 and signature.raw == expected_sig
        detail = "exact signature"

    else:
        # this vector supplies a signature with an expected verdict
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




# main takes no arguments and runs the chosen command line action
def main():
    parser = argparse.ArgumentParser(description=__doc__)

    # choose keygen sign verify or a stored vector check
    commands = parser.add_subparsers(dest="command", required=True)

    # keygen writes a public key file and a secret key file
    keygen = commands.add_parser("keygen", help="write a new public and secret key pair")
    keygen.add_argument("public_key", type=Path)
    keygen.add_argument("secret_key", type=Path)

    # sign reads the secret key and message then writes a signature
    sign = commands.add_parser("sign", help="sign the bytes in a message file")
    sign.add_argument("secret_key", type=Path)
    sign.add_argument("message", type=Path)
    sign.add_argument("signature", type=Path)

    # verify reads the public key message and signature
    verify = commands.add_parser("verify", help="verify a signature against file bytes")
    verify.add_argument("public_key", type=Path)
    verify.add_argument("message", type=Path)
    verify.add_argument("signature", type=Path)

    # sign and verify can read the same optional context file
    for command in (sign, verify):
        command.add_argument("--context-file", type=Path,
                             help="optional raw context bytes (at most 255)")

    # kind chooses the vector type and case chooses its test id
    vector = commands.add_parser("vector", help="check one stored pure FIPS 204 case")
    vector.add_argument("kind", choices=("keygen", "siggen", "sigver"))
    vector.add_argument("case", type=int, help="tcId within that vector kind")

    args = parser.parse_args()

    # build the host library before loading it
    subprocess.run(["make", "-s", "build/libmldsa_nttz.so"], cwd=ROOT, check=True)

    lib = ctypes.CDLL(str(ROOT / "build/libmldsa_nttz.so"))
    pointer, size = ctypes.c_void_p, ctypes.c_size_t

    # tell ctypes how each c function receives its arguments
    lib.mldsa44_keygen.argtypes = [pointer, pointer, pointer]
    lib.mldsa44_sign.argtypes = [pointer, pointer, size, pointer, size,
                                 pointer, size, pointer]
    lib.mldsa44_verify.argtypes = [pointer, size, pointer, size,
                                   pointer, size, pointer, size]

    # vector compares one stored case with its expected answer
    if args.command == "vector":
        run_vector(lib, args.kind, args.case)
        return

    # keygen creates a fresh key pair and saves both files
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

    # sign and verify both use exact bytes from files
    message = input_file(args.message)
    context = input_file(args.context_file) if args.context_file else b""
    if len(context) > 255:
        raise ValueError("context must be at most 255 bytes")

    if args.command == "sign":
        # the secret key signs the chosen message and context
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
        # the public key checks the saved signature against the same bytes
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
