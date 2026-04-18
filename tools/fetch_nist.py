#!/usr/bin/env python3
from pathlib import Path
from urllib.request import urlopen

COMMIT = "975de31eb83d87039ec88934fdc47d8c312b892d"
SETS = (
    "SHAKE-128-FIPS202",
    "SHAKE-256-FIPS202",
    "ML-DSA-keyGen-FIPS204",
    "ML-DSA-sigGen-FIPS204",
    "ML-DSA-sigVer-FIPS204",
)
ROOT = Path(__file__).resolve().parents[1] / "build/nist"


def main():
    for name in SETS:
        path = ROOT / name
        path.mkdir(parents=True, exist_ok=True)
        for file in ("prompt.json", "expectedResults.json"):
            dst = path / file
            if dst.exists():
                continue
            url = ("https://raw.githubusercontent.com/usnistgov/ACVP-Server/"
                   f"{COMMIT}/gen-val/json-files/{name}/{file}")
            dst.write_bytes(urlopen(url).read())
            print(f"fetched {name}/{file}")


if __name__ == "__main__":
    main()
