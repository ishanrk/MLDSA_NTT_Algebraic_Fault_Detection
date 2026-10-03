"""read archie results and check that the recovered key can forge a signature."""

import ctypes
import json
import struct
import sys
from pathlib import Path
from typing import NamedTuple

import tables

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "emu"
RECORD_BYTES = 20 + 1312 + 2420  # status plus public key plus signature
FIPS_TC_ID = 191


class Result(NamedTuple):
    sign: int
    verify: int
    calls: int
    pk: bytes
    sig: bytes


def read_record(group):
    """read the result saved in emulated ram."""
    if not group.faults.attrs.endpoint:
        raise RuntimeError("firmware did not reach emu_done")
    dumps = [node for node in group.memdumps._f_iter_nodes("CArray")
             if node.shape == (1, RECORD_BYTES)]
    if len(dumps) != 1:
        raise RuntimeError("expected one RAM dump")
    raw = bytes(dumps[0][0])
    magic, sign, verify, calls, zero_table = struct.unpack_from("<IiiII", raw)
    if magic != 0x41524348 or zero_table == 0:
        raise RuntimeError("firmware did not initialize its result")
    return Result(sign, verify, calls, raw[20:1332], raw[1332:])


def fips_case():
    """load the fixed fips case and its expected clean signature."""
    directory = ROOT / "vectors/ML-DSA-sigGen-FIPS204"
    vectors = json.loads((directory / "test_vec.json").read_text())
    answers = json.loads((directory / "expectedResults.json").read_text())
    case = next(test for group in vectors["testGroups"]
                for test in group["tests"] if test["tcId"] == FIPS_TC_ID)
    answer = next(test for group in answers["testGroups"]
                  for test in group["tests"] if test["tcId"] == FIPS_TC_ID)
    return (bytes.fromhex(case["message"]), bytes.fromhex(case["context"]),
            bytes.fromhex(case["sk"]), bytes.fromhex(answer["signature"]))


def signing_library():
    lib = ctypes.CDLL(str(ROOT / "build/libmldsa_nttz.so"))
    pointer, size = ctypes.c_void_p, ctypes.c_size_t
    lib.mldsa44_sign.argtypes = [pointer, pointer, size, pointer, size,
                                 pointer, size, pointer]
    lib.mldsa44_verify.argtypes = [pointer, size, pointer, size,
                                   pointer, size, pointer, size]
    return lib


def forge(pk, signature, message, context, lib):
    """recover s1 and use it to sign a chosen message."""
    sys.path.insert(0, str(ROOT / "demo"))
    from s1_recover import recover_s1
    from signature_forgery import reconstruct

    s1, guesses = recover_s1(signature)
    secret = reconstruct(pk, s1)
    forged = ctypes.create_string_buffer(2420)
    rnd = ctypes.create_string_buffer(32)
    if lib.mldsa44_sign(forged, secret, len(secret), message,
                        len(message), context or None, len(context), rnd) != 0:
        raise RuntimeError("equivalent key failed to sign the chosen message")
    if lib.mldsa44_verify(pk, len(pk), message, len(message), context or None,
                          len(context), forged, 2420) != 0:
        raise RuntimeError("forgery failed verification under the original public key")
    output_dir = HERE / "build"
    (output_dir / "forged.sig").write_bytes(forged.raw)
    (output_dir / "forged.message").write_bytes(message)
    (output_dir / "forged.context").write_bytes(context)
    print(f"Recovered s1 from the faulty public signature; guesses={guesses}")
    print(f"Forged for message={message!r}, context={context!r}")
    print("Forged signature: emu/build/forged.sig (verification passed under faulty.pk)")
    print("Exact forgery inputs: emu/build/forged.message and emu/build/forged.context")
    return s1


def analyze(message, context):
    """check the faulted signature and the guarded signer."""
    original_message, original_context, original_sk, expected_sig = fips_case()
    results = {}
    for variant in ("plain", "guarded"):
        with tables.open_file(HERE / f"{variant}.hdf5") as output:
            faults = list(output.root.fault._f_iter_nodes("Group"))
            if len(faults) != 1:
                raise RuntimeError("expected one ARCHIE fault experiment")
            clean = read_record(output.root.Goldenrun)
            faulted = read_record(faults[0])
            results[variant] = clean, faulted
            print(f"{variant} clean: sign={clean.sign}, verify={clean.verify}, "
                  f"NTT calls={clean.calls}")
            verification = "not run" if faulted.verify == -2 else str(faulted.verify)
            print(f"{variant} fault: sign={faulted.sign}, verify={verification}, "
                  f"NTT calls={faulted.calls}")
            if (clean.sign, clean.verify, clean.calls) != (0, 0, 17):
                raise RuntimeError(f"{variant} clean signer failed")
            if clean.sig != expected_sig:
                raise RuntimeError(f"{variant} clean signature differs from FIPS case {FIPS_TC_ID}")

    clean, plain = results["plain"]
    _, guarded = results["guarded"]
    if (plain.sign, plain.verify, plain.calls) != (0, 0, 17) or plain.sig == clean.sig:
        raise RuntimeError("faulted plain signer did not release a verifying, changed signature")
    if (guarded.sign, guarded.verify, guarded.calls) != (-1, -2, 13):
        raise RuntimeError("guard did not abort on the first faulty nonce NTT")
    if guarded.sig != bytes([0xa5]) * 2420:
        raise RuntimeError("guarded signer wrote a signature")

    lib = signing_library()
    if lib.mldsa44_verify(plain.pk, len(plain.pk), original_message,
                          len(original_message), original_context,
                          len(original_context), plain.sig, len(plain.sig)) != 0:
        raise RuntimeError("host verifier rejected the faulty plain signature")

    (HERE / "build/clean.sig").write_bytes(clean.sig)
    (HERE / "build/faulty.pk").write_bytes(plain.pk)
    (HERE / "build/faulty.sig").write_bytes(plain.sig)
    (HERE / "build/faulty.message").write_bytes(original_message)
    (HERE / "build/faulty.context").write_bytes(original_context)
    print(f"Clean signature: emu/build/clean.sig (exact FIPS case {FIPS_TC_ID} match)")
    print("Faulty plain signature: emu/build/faulty.sig "
          "(different from clean; host verification passed)")
    print("Faulty signature inputs: emu/build/faulty.message and emu/build/faulty.context")
    print("Public key for both signatures: emu/build/faulty.pk")
    recovered_s1 = forge(plain.pk, plain.sig, message, context, lib)
    from signature_forgery import decode_bits
    original_s1 = [decode_bits(original_sk[128 + 96 * row:224 + 96 * row],
                               3, 2, True) for row in range(4)]
    if recovered_s1 != original_s1:
        raise RuntimeError("recovered s1 differs from the FIPS test key")
    print("Post-attack check: recovered s1 matches the FIPS secret key")
    print("GUARD_REJECTED; all checks passed")
