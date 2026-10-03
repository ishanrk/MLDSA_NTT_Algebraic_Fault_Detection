#!/usr/bin/env python3
"""build the plain cortex m4 signer and test one fault."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from attack_demo import RECORD_BYTES, analyze

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "emu"



# args are the command followed by its arguments
# cwd is the directory where the command runs
# quiet hides output unless the command fails
def run(*args, cwd=ROOT, quiet=False):
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, text=True,
                            stdout=subprocess.PIPE if quiet else None,
                            stderr=subprocess.STDOUT if quiet else None)
    if result.returncode:
        if quiet:
            print(result.stdout, file=sys.stderr)
        result.check_returncode()



# elf is the path to the arm firmware file
# return a map from symbol names to addresses
def symbols(elf):
    listing = subprocess.check_output(["arm-none-eabi-nm", "-n", str(elf)], text=True)
    names = {}
    for line in listing.splitlines():
        parts = line.split()
        if len(parts) == 3:
            names[parts[2]] = int(parts[0], 16)

    # use addresses from this exact firmware build
    return names



# variant names the firmware build such as plain
# archie is the path to the archie checkout
# write the qemu and fault configs for that build
def write_configs(variant, archie):
    elf = HERE / "build" / f"{variant}.elf"
    names = symbols(elf)

    # find the ram pointer and the table that will replace it
    pointer = names["mldsa_archie_twiddles"]
    zero_table = names["emu_zero_zetas"]
    marker = names["mldsa_archie_nonce_start"]
    result = names["emu_result"]

    # archie uses this config to run the signer in qemu
    qemu = {
        "qemu": str(archie / "qemu/build/qemu-system-arm"),
        "bios": "", "kernel": str(elf),
        "plugin": str(archie / "faultplugin/libfaultplugin.so"),
        "machine": "mps2-an386", "additional_qemu_args": "-nographic",
    }

    # overwrite the pointer when the first nonce ntt starts
    # fault_mask is the new address stored in that pointer
    fault = {
        "max_instruction_count": 100_000_000,
        "start": {"address": names["mldsa44_sign"], "counter": 1},
        "end": {"address": names["emu_done"], "counter": 1},
        # archie dumps the public key and signature stored in emu_result
        "memorydump": [{"address": result, "length": RECORD_BYTES}],
        "faults": [[{
            "fault_address": [pointer], "fault_type": "data",
            "fault_model": "overwrite", "num_bytes": 4,
            "fault_mask": [zero_table], "fault_lifespan": [0],
            "trigger_address": [marker], "trigger_counter": [1],
        }]],
    }
    # write the qemu settings and the fault addresses for this build
    (HERE / f"qemu-{variant}.json").write_text(json.dumps(qemu, indent=2) + "\n")
    (HERE / f"fault-{variant}.json").write_text(json.dumps(fault, indent=2) + "\n")

    print("\nfault injection")
    print(f"  overwrite pointer at 0x{pointer:x}")
    print(f"  new value is zero table address 0x{zero_table:x}")
    print(f"  trigger at 0x{marker:x}")



# variant names the firmware build to run
# archie is the path to the archie checkout
# run one clean signing and one signing with the injected fault
def run_archie(variant, archie):
    print(f"\n{variant} simulation", flush=True)
    print("  running a clean reference and one fault experiment", flush=True)

    # overwrite lets archie replace an old result file
    run(sys.executable, archie / "controller.py", "--debug", "--overwrite",
        "--fault", HERE / f"fault-{variant}.json", "--qemu",
        HERE / f"qemu-{variant}.json", HERE / f"{variant}.hdf5",
        cwd=HERE, quiet=True)

    # the controller stores both runs in the same hdf5 file
    # make sure the fault was injected once
    if (HERE / "log_0.txt").read_text(errors="replace").count("Inject memory fault") != 1:
        raise RuntimeError(f"ARCHIE did not inject exactly once: {variant}")
    # keep the fault log and clean log under names tied to this build
    for path in HERE.glob("log_*.txt"):
        path.rename(HERE / f"{variant}-{path.name}")
    print("  memory injections: 1")



# read options from the command line
def main():
    parser = argparse.ArgumentParser(description=__doc__)

    # convert the archie path to a path object
    parser.add_argument("--archie", type=Path,
                        default=Path.home() / "archie-demo" / "archie")

    # true when the flag is present
    parser.add_argument("--analyze-only", action="store_true")

    # choose message text or a file but not both
    message_input = parser.add_mutually_exclusive_group()
    message_input.add_argument("--message", default="New message chosen by the attacker")
    message_input.add_argument("--message-file", type=Path,
                               help="read exact forgery message bytes from a file")

    # make the same choice for context
    context_input = parser.add_mutually_exclusive_group()
    context_input.add_argument("--context", default="")
    context_input.add_argument("--context-file", type=Path,
                               help="read exact forgery context bytes from a file")

    # read the options into args
    args = parser.parse_args()

    # files keep their bytes and text becomes utf8 bytes
    message = args.message_file.read_bytes() if args.message_file else args.message.encode()
    context = args.context_file.read_bytes() if args.context_file else args.context.encode()

    # count bytes rather than characters
    if len(context) > 255:
        parser.error("context must be at most 255 bytes")

    # skip the build and simulation with --analyze-only
    if not args.analyze_only:
        # check the required archie files
        archie = args.archie.resolve()
        for path in (archie / "controller.py", archie / "qemu/build/qemu-system-arm",
                     archie / "faultplugin/libfaultplugin.so"):
            if not path.is_file():
                raise FileNotFoundError(path)

        # build the firmware and host library
        run("make", "-C", HERE, "build/plain.elf")
        run("make", "build/libmldsa_nttz.so")

        # run a clean signer and one fault experiment
        write_configs("plain", archie)
        run_archie("plain", archie)

    # analyze the result and forge a signature
    analyze(message, context)



if __name__ == "__main__":
    main()
