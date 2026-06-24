#!/usr/bin/env python3
#
# Copyright (c) 2026
#
# SPDX-License-Identifier: Apache-2.0

"""Generate HSS payload YAML and optionally invoke hss-payload-generator."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

HART_CHOICES = ("u54_1", "u54_2", "u54_3", "u54_4")
PRIV_MODE_CHOICES = ("prv_m", "prv_s", "prv_u")


def yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def default_hart_layout(variant: str) -> tuple[str, list[str]]:
    owner_hart = "u54_1"
    secondary_harts: list[str] = []

    if variant == "u54-smp":
        secondary_harts = ["u54_2", "u54_3", "u54_4"]

    return owner_hart, secondary_harts


def render_yaml(
    elf_path: Path,
    image_name: str,
    payload_name: str,
    load_addr: str,
    owner_hart: str,
    secondary_harts: list[str],
    priv_mode: str,
    skip_opensbi: bool,
) -> str:
    lines = [
        f"set-name: {yaml_quote(image_name)}",
        "",
        "hart-entry-points:",
        f"  {owner_hart}: {yaml_quote(load_addr)}",
    ]

    for hart in secondary_harts:
        lines.append(f"  {hart}: {yaml_quote(load_addr)}")

    lines.extend(
        [
            "",
            "payloads:",
            f"  {yaml_quote(str(elf_path))}:",
            f"    exec-addr: {yaml_quote(load_addr)}",
            f"    owner-hart: {owner_hart}",
        ]
    )

    for hart in secondary_harts:
        lines.append(f"    secondary-hart: {hart}")

    lines.extend(
        [
            f"    priv-mode: {priv_mode}",
            f"    skip-opensbi: {'true' if skip_opensbi else 'false'}",
            f"    payload-name: {yaml_quote(payload_name)}",
            "",
        ]
    )

    return "\n".join(lines)


def find_default_yaml_path(output_path: Path) -> Path:
    return output_path.with_suffix(".yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an HSS payload YAML for mpfs_discovery and optionally build the payload"
    )
    parser.add_argument(
        "--elf",
        required=True,
        help="Path to the Zephyr ELF file, for example build/blinky/zephyr/zephyr.elf",
    )
    parser.add_argument(
        "--variant",
        choices=("u54", "u54-smp"),
        default="u54",
        help="Board runtime variant to describe in the HSS payload",
    )
    parser.add_argument(
        "--load-addr",
        default="0x80000000",
        help="Load and entry address used by HSS for the Zephyr payload",
    )
    parser.add_argument(
        "--owner-hart",
        choices=HART_CHOICES,
        help="Override the owner hart derived from --variant",
    )
    parser.add_argument(
        "--secondary-hart",
        action="append",
        choices=HART_CHOICES,
        default=[],
        help="Add a secondary hart. May be passed multiple times. Overrides the default SMP secondary set when used.",
    )
    parser.add_argument(
        "--image-name",
        default="mpfs-discovery-zephyr",
        help="HSS image name stored in the generated payload header",
    )
    parser.add_argument(
        "--payload-name",
        default="zephyr",
        help="Human-readable payload name stored in the HSS payload",
    )
    parser.add_argument(
        "--output",
        help="Output .bin payload path. Defaults next to the ELF.",
    )
    parser.add_argument(
        "--yaml-out",
        help="Output YAML path. Defaults next to the payload output file.",
    )
    parser.add_argument(
        "--hss-payload-generator",
        help="Path to the HSS payload generator executable. If omitted, only the YAML is generated.",
    )
    parser.add_argument(
        "--priv-mode",
        choices=PRIV_MODE_CHOICES,
        default="prv_m",
        help="Privilege mode recorded in the HSS YAML",
    )
    parser.add_argument(
        "--skip-opensbi",
        dest="skip_opensbi",
        action="store_true",
        default=True,
        help="Emit skip-opensbi: true in the HSS YAML (default)",
    )
    parser.add_argument(
        "--no-skip-opensbi",
        dest="skip_opensbi",
        action="store_false",
        help="Emit skip-opensbi: false in the HSS YAML",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Pass -v to hss-payload-generator when it is executed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    elf_path = Path(args.elf).expanduser().resolve()
    if not elf_path.is_file():
        print(f"ELF file not found: {elf_path}", file=sys.stderr)
        return 2

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        suffix = f"_{args.variant}_hss.bin"
        output_path = elf_path.with_name(elf_path.stem + suffix)

    yaml_path = (
        Path(args.yaml_out).expanduser().resolve()
        if args.yaml_out
        else find_default_yaml_path(output_path)
    )

    default_owner_hart, default_secondary_harts = default_hart_layout(args.variant)
    owner_hart = args.owner_hart or default_owner_hart
    secondary_harts = list(args.secondary_hart) if args.secondary_hart else list(default_secondary_harts)

    if owner_hart in secondary_harts:
        print(f"Owner hart {owner_hart} cannot also be a secondary hart.", file=sys.stderr)
        return 2

    yaml_text = render_yaml(
        elf_path=elf_path,
        image_name=args.image_name,
        payload_name=args.payload_name,
        load_addr=args.load_addr,
        owner_hart=owner_hart,
        secondary_harts=secondary_harts,
        priv_mode=args.priv_mode,
        skip_opensbi=args.skip_opensbi,
    )

    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(yaml_text, encoding="utf-8")
    print(f"Wrote HSS payload YAML: {yaml_path}")

    if not args.hss_payload_generator:
        print("YAML generated only. Re-run with --hss-payload-generator to build the payload binary.")
        return 0

    generator = Path(args.hss_payload_generator).expanduser().resolve()
    if not generator.is_file():
        print(f"hss-payload-generator not found: {generator}", file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [str(generator), "-c", str(yaml_path)]
    if args.verbose:
        cmd.append("-v")
    cmd.append(str(output_path))

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Wrote HSS payload binary: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
