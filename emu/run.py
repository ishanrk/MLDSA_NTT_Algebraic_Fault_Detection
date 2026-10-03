#!/usr/bin/env python3
"""build two cortex m4 signers and test a fault in each."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from attack_demo import RECORD_BYTES, analyze

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "emu"


def run(*args, cwd=ROOT, quiet=False):
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, text=True,
                            stdout=subprocess.PIPE if quiet else None,
                            stderr=subprocess.STDOUT if quiet else None)
    if result.returncode:
        if quiet:
            print(result.stdout, file=sys.stderr)
        result.check_returncode()


def symbols(elf):
    """read symbol addresses from the elf file."""
    listing = subprocess.check_output(["arm-none-eabi-nm", "-n", str(elf)], text=True)
    names = {}
    for line in listing.splitlines():
        parts = line.split()
        if len(parts) == 3:
            names[parts[2]] = int(parts[0], 16)

    # keep each symbol name with its address
    return names


def write_configs(variant, archie):
    """set up the fault for one signer."""
    elf = HERE / "build" / f"{variant}.elf"
    names = symbols(elf)

    # find the pointer and the zero table used by the fault
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
    # archie runs one pointer overwrite
    # fault_mask holds the replacement pointer value
    fault = {
        "max_instruction_count": 100_000_000,
        "start": {"address": names["mldsa44_sign"], "counter": 1},
        "end": {"address": names["emu_done"], "counter": 1},
        "memorydump": [{"address": result, "length": RECORD_BYTES}],
        "faults": [[{
            "fault_address": [pointer], "fault_type": "data",
            "fault_model": "overwrite", "num_bytes": 4,
            "fault_mask": [zero_table], "fault_lifespan": [0],
            "trigger_address": [marker], "trigger_counter": [1],
        }]],
    }
    (HERE / f"qemu-{variant}.json").write_text(json.dumps(qemu, indent=2) + "\n")
    (HERE / f"fault-{variant}.json").write_text(json.dumps(fault, indent=2) + "\n")
    print(f"{variant}: overwrite RAM pointer 0x{pointer:x} with zero-table address "
          f"0x{zero_table:x} at marker 0x{marker:x}")


def run_archie(variant, archie):
    """run a clean signing and a faulted signing."""
    print(f"{variant}: running clean reference, then one fault experiment", flush=True)
    # overwrite lets archie replace an old result file
    run(sys.executable, archie / "controller.py", "--debug", "--overwrite",
        "--fault", HERE / f"fault-{variant}.json", "--qemu",
        HERE / f"qemu-{variant}.json", HERE / f"{variant}.hdf5",
        cwd=HERE, quiet=True)

    # make sure the fault was injected once
    if (HERE / "log_0.txt").read_text(errors="replace").count("Inject memory fault") != 1:
        raise RuntimeError(f"ARCHIE did not inject exactly once: {variant}")
    for path in HERE.glob("log_*.txt"):
        path.rename(HERE / f"{variant}-{path.name}")
    print(f"{variant}: ARCHIE memory injections: 1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archie", type=Path,
                        default=Path.home() / "archie-demo" / "archie")
    parser.add_argument("--analyze-only", action="store_true")
    message_input = parser.add_mutually_exclusive_group()
    message_input.add_argument("--message", default="New message chosen by the attacker")
    message_input.add_argument("--message-file", type=Path,
                               help="read exact forgery message bytes from a file")
    context_input = parser.add_mutually_exclusive_group()
    context_input.add_argument("--context", default="")
    context_input.add_argument("--context-file", type=Path,
                               help="read exact forgery context bytes from a file")
    args = parser.parse_args()
    message = args.message_file.read_bytes() if args.message_file else args.message.encode()
    context = args.context_file.read_bytes() if args.context_file else args.context.encode()
    if len(context) > 255:
        parser.error("context must be at most 255 bytes")
    if not args.analyze_only:
        archie = args.archie.resolve()
        for path in (archie / "controller.py", archie / "qemu/build/qemu-system-arm",
                     archie / "faultplugin/libfaultplugin.so"):
            if not path.is_file():
                raise FileNotFoundError(path)
        run("make", "-C", HERE)
        run("make", "build/libmldsa_nttz.so")
        for variant in ("plain", "guarded"):
            write_configs(variant, archie)
            run_archie(variant, archie)
    analyze(message, context)


if __name__ == "__main__":
    main()
