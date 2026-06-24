# MPFS Discovery HSS Tools

This repository provides a focused helper for preparing HSS payloads from
Zephyr ELF files on the Microchip PolarFire SoC Discovery Kit.

## Why this repository exists

Building a Zephyr application gives you an ELF, but booting through the normal
PolarFire SoC flow usually requires an HSS payload description and a generated
payload image.

This repository keeps that packaging step separate from:

- the board definition
- the application source tree
- the long-form documentation

## Included tool

- `mpfs_discovery_hss_payload.py`

## What the helper does

The helper automates the repetitive parts of the flow:

1. take a built Zephyr ELF
2. generate an HSS YAML payload description
3. optionally call the official `hss-payload-generator`
4. produce a final bootable payload binary

## What the helper does not do

The helper does not:

- build Zephyr for you
- flash the board for you
- replace HSS itself
- build a full Linux plus Zephyr AMP payload set
- understand every custom FPGA design automatically

## Typical use cases

Use this repository when you want:

- a quick `u54` Zephyr payload
- an `u54/smp` Zephyr payload
- a simple single-payload custom design flow
- a repeatable packaging command for local work or CI

## Requirements

You need:

- Python 3
- a Zephyr ELF already built
- the official `hss-payload-generator` if you want the final `.bin` payload

## Supported variants

- `u54`
- `u54-smp`

Default behavior:

- `u54` uses owner hart `u54_1`
- `u54-smp` uses owner hart `u54_1` and secondary harts `u54_2` to `u54_4`
- load address defaults to `0x80000000`
- privilege mode defaults to `prv_m`
- `skip-opensbi` defaults to `true`

## Quick start

Generate YAML only:

```console
python3 mpfs_discovery_hss_payload.py \
  --variant u54 \
  --elf build/blinky/zephyr/zephyr.elf
```

Generate YAML and final payload binary:

```console
python3 mpfs_discovery_hss_payload.py \
  --variant u54 \
  --elf build/blinky/zephyr/zephyr.elf \
  --output build/blinky/zephyr/mpfs_discovery_blinky_u54_hss.bin \
  --yaml-out build/blinky/zephyr/mpfs_discovery_blinky_u54_hss.yaml \
  --hss-payload-generator /path/to/hss-payload-generator
```

## Recommended workflow

Use this sequence:

1. build the Zephyr application
2. verify the correct board target was used
3. run this helper to generate YAML
4. inspect the YAML during bring-up
5. run the official payload generator
6. copy the resulting payload to the medium used by your HSS boot flow

## Custom design overrides available on the command line

For simple custom designs, the helper already supports:

- `--load-addr`
- `--owner-hart`
- repeated `--secondary-hart`
- `--priv-mode`
- `--skip-opensbi`
- `--no-skip-opensbi`

Example:

```console
python3 mpfs_discovery_hss_payload.py \
  --variant u54 \
  --elf build/my_app/zephyr/zephyr.elf \
  --load-addr 0x90000000 \
  --owner-hart u54_4 \
  --priv-mode prv_m \
  --hss-payload-generator /path/to/hss-payload-generator
```

## When the helper is enough

You usually do not need to modify the script when:

- the custom FPGA design only changes peripheral routing
- the Zephyr payload still lives in the same memory window
- one Zephyr image still boots on one owner hart or on the normal U54 SMP set

In those cases, the real changes usually belong in:

- the board DTS files
- an application overlay
- the application code

## When you should stop and write a dedicated HSS YAML

Do not force this helper too far. Move to a dedicated HSS YAML or extend the
tool deliberately when:

- you need several payloads in one image
- you are building a real AMP Linux plus Zephyr system
- you need a supervisor-mode flow through OpenSBI
- different payloads need different ownership or boot policies

## Expected outputs

Depending on the command line, the helper can produce:

- a YAML description only
- a YAML description plus a final `.bin` payload

Keeping the YAML is useful because it gives you a readable intermediate artifact
for review and debugging.
