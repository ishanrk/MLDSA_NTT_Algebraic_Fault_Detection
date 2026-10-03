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



# one result contains the firmware status plus its key and signature
class Result(NamedTuple):
    sign: int
    verify: int
    calls: int
    pk: bytes
    sig: bytes



# group is one clean or faulted run from the archie result file
# return its signing status and the bytes saved by the firmware
def read_record(group):
    # endpoint means the firmware reached emu_done
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

    # zero return codes mean signing and verification succeeded
    # calls counts forward ntt transforms during signing
    # the first 20 bytes are status followed by the public key and signature
    return Result(sign, verify, calls, raw[20:1332], raw[1332:])



# this takes no arguments
# return the message and context for fips case 191
# also return its secret key and expected clean signature
def fips_case():
    # this vector provides the original secret and the clean answer
    # runner.c gets the matching public key from fips_case.h
    directory = ROOT / "vectors/ML-DSA-sigGen-FIPS204"
    vectors = json.loads((directory / "test_vec.json").read_text())
    answers = json.loads((directory / "expectedResults.json").read_text())

    case = next(test for group in vectors["testGroups"]
                for test in group["tests"] if test["tcId"] == FIPS_TC_ID)
    answer = next(test for group in answers["testGroups"]
                  for test in group["tests"] if test["tcId"] == FIPS_TC_ID)

    return (bytes.fromhex(case["message"]), bytes.fromhex(case["context"]),
            bytes.fromhex(case["sk"]), bytes.fromhex(answer["signature"]))



# this takes no arguments
# return the host mldsa library with sign and verify argument types set
def signing_library():
    lib = ctypes.CDLL(str(ROOT / "build/libmldsa_nttz.so"))
    pointer, size = ctypes.c_void_p, ctypes.c_size_t

    # ctypes needs the c argument layout before these calls
    lib.mldsa44_sign.argtypes = [pointer, pointer, size, pointer, size,
                                 pointer, size, pointer]
    lib.mldsa44_verify.argtypes = [pointer, size, pointer, size,
                                   pointer, size, pointer, size]
    return lib



# pk is the original 1312 byte public key
# signature is the 2420 byte faulty signature
# message and context are the new bytes chosen for the forgery
# lib is the host mldsa library returned by signing_library
# return the four recovered s1 polynomials
def forge(pk, signature, message, context, lib):
    sys.path.insert(0, str(ROOT / "demo"))
    from s1_recover import recover_s1
    from signature_forgery import reconstruct

    # the faulty public signature is enough to recover s1
    s1, guesses = recover_s1(signature)

    # rebuild a different secret key for the same public key
    secret = reconstruct(pk, s1)

    # this signing happens on the host after the qemu fault run
    forged = ctypes.create_string_buffer(2420)
    # use zero random bytes for this demo signature
    rnd = ctypes.create_string_buffer(32)
    if lib.mldsa44_sign(forged, secret, len(secret), message,
                        len(message), context or None, len(context), rnd) != 0:
        raise RuntimeError("equivalent key failed to sign the chosen message")

    # check the new signature against the original public key
    if lib.mldsa44_verify(pk, len(pk), message, len(message), context or None,
                          len(context), forged, 2420) != 0:
        raise RuntimeError("forgery failed verification under the original public key")

    # save the exact key and signature used in this check
    # reconstruct gives this key a fresh nonce key so it differs from fips sk
    output_dir = HERE / "build"
    secret_path = output_dir / "forged.sk"
    secret_path.write_bytes(secret)
    secret_path.chmod(0o600)
    (output_dir / "forged.sig").write_bytes(forged.raw)
    # these files hold the exact bytes needed to verify forged.sig again
    (output_dir / "forged.message").write_bytes(message)
    (output_dir / "forged.context").write_bytes(context)

    print("\nforgery")
    print("  recovered s1 from the faulty signature")
    print(f"  missing coefficient guesses: {guesses}")
    print("  forged secret key: emu/build/forged.sk")
    print(f"  message bytes: {message!r}")
    print("  message file: emu/build/forged.message")
    print(f"  context bytes: {context!r}")
    print("  context file: emu/build/forged.context")
    print("  forged signature: emu/build/forged.sig")
    print(f"  signature verified under emu/build/fips{FIPS_TC_ID}.pk")

    return s1



# message and context are the new bytes chosen for the forgery
# read plain.hdf5 and check its clean and faulted runs
def analyze(message, context):
    # the vector secret is used only for the final recovery check
    original_message, original_context, original_sk, expected_sig = fips_case()

    # archie stores the clean run and the fault run in one file
    with tables.open_file(HERE / "plain.hdf5") as output:
        faults = list(output.root.fault._f_iter_nodes("Group"))
        if len(faults) != 1:
            raise RuntimeError("expected one ARCHIE fault experiment")
        # goldenrun has no fault and the other record has one overwrite
        clean = read_record(output.root.Goldenrun)
        plain = read_record(faults[0])

    print("\nsigning results")
    print(f"  clean: sign={clean.sign} verify={clean.verify} NTT calls={clean.calls}")
    print(f"  fault: sign={plain.sign} verify={plain.verify} NTT calls={plain.calls}")

    # twelve ntt calls transform the key parts
    # four transform nonce rows and one transforms the challenge
    # the fixed key message context and rnd give the exact fips signature
    if (clean.sign, clean.verify, clean.calls) != (0, 0, 17):
        raise RuntimeError("plain clean signer failed")
    if clean.sig != expected_sig:
        raise RuntimeError(f"plain clean signature differs from FIPS case {FIPS_TC_ID}")

    # the fault must change the signature without breaking verification
    if (plain.sign, plain.verify, plain.calls) != (0, 0, 17) or plain.sig == clean.sig:
        raise RuntimeError("faulted plain signer did not release a verifying, changed signature")

    # verify once more outside qemu with the host library
    lib = signing_library()
    if lib.mldsa44_verify(plain.pk, len(plain.pk), original_message,
                          len(original_message), original_context,
                          len(original_context), plain.sig, len(plain.sig)) != 0:
        raise RuntimeError("host verifier rejected the faulty plain signature")

    # save the extracted bytes for separate checks from the command line
    # fips191.pk is the same public key used in both firmware runs
    (HERE / "build/clean.sig").write_bytes(clean.sig)
    (HERE / f"build/fips{FIPS_TC_ID}.pk").write_bytes(plain.pk)
    (HERE / "build/faulty.sig").write_bytes(plain.sig)
    # faulty.sig signs the original fips message with its original context
    (HERE / "build/faulty.message").write_bytes(original_message)
    (HERE / "build/faulty.context").write_bytes(original_context)
    print("\nsignature files")
    print("  clean signature: emu/build/clean.sig")
    print(f"  clean signature matches FIPS case {FIPS_TC_ID}")
    print("  faulty signature: emu/build/faulty.sig")
    print("  faulty signature differs from clean and passed host verification")
    print("  message: emu/build/faulty.message")
    print("  context: emu/build/faulty.context")
    print(f"  public key: emu/build/fips{FIPS_TC_ID}.pk")

    recovered_s1 = forge(plain.pk, plain.sig, message, context, lib)

    # compare with the fips secret only after the forgery succeeds
    from signature_forgery import decode_bits
    original_s1 = [decode_bits(original_sk[128 + 96 * row:224 + 96 * row],
                               3, 2, True) for row in range(4)]
    if recovered_s1 != original_s1:
        raise RuntimeError("recovered s1 differs from the FIPS test key")

    print("  recovered s1 matches the FIPS secret key")
