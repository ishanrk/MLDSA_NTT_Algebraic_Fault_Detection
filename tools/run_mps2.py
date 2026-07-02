#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, env=None):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                       timeout=60, env=env)
    out = p.stdout + p.stderr
    if p.returncode:
        raise SystemExit(f"command failed with status {p.returncode}\n{out}")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--prior', action='store_true')
    args = p.parse_args()
    qemu = os.environ.get("QEMU", "qemu-system-arm")
    cc = os.environ.get("ARM_CC", "arm-none-eabi-gcc")
    env = os.environ.copy()
    if "QEMU_LIBDIR" in env:
        env["LD_LIBRARY_PATH"] = (env["QEMU_LIBDIR"] + os.pathsep +
                                  env.get("LD_LIBRARY_PATH", ""))
    elf = 'build/arm/mps2_prior.elf' if args.prior else 'build/arm/mps2.elf'
    dst = ROOT / ('test/qemu-mps2-an386-prior.json' if args.prior else
                  'test/qemu-mps2-an386.json')
    cmd = [qemu, "-M", "mps2-an386", "-kernel", elf,
           "-nographic", "-semihosting-config", "enable=on,target=native",
           "-no-reboot"]
    out = run(cmd, env)
    cases = ("SHAKE PASS", "NTT zero PASS", "NTT basis PASS",
             "NTT boundary PASS", "NTT fixed random PASS", "KEYGEN PASS",
             "SIGN PASS", "VERIFY valid PASS", "VERIFY modified message PASS",
             "VERIFY modified signature PASS")
    if args.prior:
        cases = ('PRIOR arithmetic PASS', 'PRIOR NTT 8 cases PASS',
                 'PRIOR single faults 36 cases PASS',
                 'PRIOR cancelling fault pairs 30 cases PASS') + cases + (
                     'PRIOR scheme fault propagation PASS',)
    if out.splitlines() != list(cases):
        raise SystemExit(f"unexpected correctness output\n{out}")
    data = {
        "purpose": "functional validation only",
        "target": "QEMU mps2-an386 Cortex M4 emulator",
        "physical_board": False,
        "physical_measurements": "pending",
        "compiler": run([cc, "--version"]).splitlines()[0],
        "emulator": run([qemu, "--version"], env).splitlines()[0],
        "cases": list(cases),
        "command": [Path(qemu).name] + cmd[1:],
    }
    dst.write_text(json.dumps(data, indent=2) + "\n")
    print(out, end="")
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
