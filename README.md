# automate_vmx_4eve

Fast installer for Juniper vMX bundles into EVE-NG.

## What It Does
- Extracts a `vmx-bundle-<version>.tgz`
- Finds required VCP/VFP images
- Installs images into EVE-NG naming format
- Optionally runs EVE-NG `fixpermissions`

## Requirements
- Python 3.10+
- Access to EVE-NG filesystem (default: `/opt/unetlab/addons/qemu`)
- vMX bundle file (for example: `vmx-bundle-24.2R1.15.tgz`)

## Quick Start
```bash
python3 automate_vmx.py /path/to/vmx-bundle-24.2R1.15.tgz
```

Or pass only version if file is in current directory:
```bash
python3 automate_vmx.py 24.2R1.15
```

## Useful Options
```bash
python3 automate_vmx.py <bundle-or-version> \
  --eve-root /opt/unetlab/addons/qemu \
  --keep-extracted \
  --skip-fixpermissions \
  --vfp-metadata-mode auto
```

`--vfp-metadata-mode` values:
- `auto` (default): copy first two VFP metadata disks if found
- `none`: skip VFP metadata disks

## Output
Creates:
- `vmxvcp-<version>-domestic-VCP`
- `vmxvfp-<version>-domestic-VFP`

under the selected EVE-NG root.

## Credits
- Project owner: Moshiko Nayman
