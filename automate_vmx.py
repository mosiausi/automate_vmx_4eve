"""Automate vMX bundle extraction and EVE-NG image installation.

Credits:
- Original project and ownership: Moshiko Nayman

Version:
- 1.1.0
"""

import argparse
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

__version__ = "1.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a Juniper vMX bundle and install VCP/VFP images for EVE-NG."
    )
    parser.add_argument(
        "bundle",
        help="Path to vmx-bundle-<version>.tgz or just the version string.",
    )
    parser.add_argument(
        "--eve-root",
        default="/opt/unetlab/addons/qemu",
        help="EVE-NG QEMU images root directory.",
    )
    parser.add_argument(
        "--keep-extracted",
        action="store_true",
        help="Keep the temporary extracted bundle directory for inspection.",
    )
    parser.add_argument(
        "--skip-fixpermissions",
        action="store_true",
        help="Skip running /opt/unetlab/wrappers/unl_wrapper -a fixpermissions.",
    )
    parser.add_argument(
        "--vfp-metadata-mode",
        choices=["auto", "none"],
        default="auto",
        help=(
            "How to handle metadata-usb-fpc*.img for VFP: "
            "'auto' copies the first two (fpc0/fpc1), 'none' skips VFP metadata entirely."
        ),
    )
    return parser.parse_args()


def resolve_bundle_path(bundle_arg: str) -> Path:
    candidate = Path(bundle_arg)
    if candidate.is_file():
        return candidate.resolve()

    guessed = Path(f"vmx-bundle-{bundle_arg}.tgz")
    if guessed.is_file():
        return guessed.resolve()

    raise FileNotFoundError(
        f"Bundle not found: '{bundle_arg}'. Expected a file path or vmx-bundle-<version>.tgz in the current directory."
    )


def derive_version(bundle_path: Path) -> str:
    match = re.match(r"vmx-bundle-(.+)\.t(?:ar\.)?gz$", bundle_path.name)
    if match:
        return match.group(1)
    return bundle_path.stem


def safe_extract(tar: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in tar.getmembers():
        member_path = (destination / member.name).resolve()
        if not str(member_path).startswith(str(destination)):
            raise ValueError(f"Unsafe path in archive: {member.name}")
    tar.extractall(destination)


def find_images_dir(extracted_root: Path) -> Path:
    image_dirs = sorted(
        path for path in extracted_root.rglob("images") if path.is_dir()
    )
    for image_dir in image_dirs:
        if list(image_dir.glob("junos-vmx-x86-64-*.qcow2")):
            return image_dir
    raise FileNotFoundError("Could not find the extracted vMX images directory.")


def require_one(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"Missing required file matching '{pattern}' in {directory}")
    if len(matches) > 1:
        raise FileExistsError(
            f"Expected one file matching '{pattern}' in {directory}, found: {', '.join(path.name for path in matches)}"
        )
    return matches[0]


def optional_many(directory: Path, pattern: str) -> list[Path]:
    return sorted(directory.glob(pattern))


def metadata_fpc_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"fpc(\d+)", path.name)
    if match:
        return (int(match.group(1)), path.name)
    return (sys.maxsize, path.name)


def copy_file(source: Path, destination: Path) -> None:
    shutil.copy2(source, destination)
    print(f"Copied {source.name} -> {destination}")


def install_vmx(
    bundle_path: Path,
    eve_root: Path,
    keep_extracted: bool,
    skip_fixpermissions: bool,
    vfp_metadata_mode: str,
) -> None:
    version = derive_version(bundle_path)
    vcp_dest = eve_root / f"vmxvcp-{version}-domestic-VCP"
    vfp_dest = eve_root / f"vmxvfp-{version}-domestic-VFP"

    temp_dir_context = tempfile.TemporaryDirectory(prefix="vmx-bundle-")
    temp_dir = Path(temp_dir_context.name)

    try:
        print(f"Extracting {bundle_path} into {temp_dir}")
        with tarfile.open(bundle_path, "r:gz") as tar:
            safe_extract(tar, temp_dir)

        images_dir = find_images_dir(temp_dir)
        print(f"Using images directory: {images_dir}")

        vcp_dest.mkdir(parents=True, exist_ok=True)
        vfp_dest.mkdir(parents=True, exist_ok=True)

        junos_image = require_one(images_dir, "junos-vmx-x86-64-*.qcow2")
        vmxhdd_image = require_one(images_dir, "vmxhdd.img")
        metadata_re = require_one(images_dir, "metadata-usb-re.img")
        vfpc_image = require_one(images_dir, "vFPC-*.img")
        metadata_fpcs = sorted(
            optional_many(images_dir, "metadata-usb-fpc*.img"),
            key=metadata_fpc_sort_key,
        )

        copy_file(junos_image, vcp_dest / "virtioa.qcow2")
        copy_file(vmxhdd_image, vcp_dest / "virtiob.qcow2")
        copy_file(metadata_re, vcp_dest / "virtioc.qcow2")

        copy_file(vfpc_image, vfp_dest / "virtioa.qcow2")
        if vfp_metadata_mode == "auto":
            vfp_metadata_targets = ["virtiob.qcow2", "virtioc.qcow2"]
            selected_metadata_fpcs = metadata_fpcs[: len(vfp_metadata_targets)]
            if len(metadata_fpcs) > len(vfp_metadata_targets):
                skipped = ", ".join(path.name for path in metadata_fpcs[len(vfp_metadata_targets) :])
                print(
                    "Detected additional VFP metadata disks not used by EVE-NG and skipping them: "
                    f"{skipped}"
                )
            for metadata_path, target_name in zip(selected_metadata_fpcs, vfp_metadata_targets):
                copy_file(metadata_path, vfp_dest / target_name)
        else:
            print("Skipping VFP metadata disks by request (--vfp-metadata-mode none)")

        if not skip_fixpermissions:
            wrapper = Path("/opt/unetlab/wrappers/unl_wrapper")
            if wrapper.exists():
                print("Running EVE-NG fixpermissions")
                subprocess.run([str(wrapper), "-a", "fixpermissions"], check=True)
            else:
                print("Skipping fixpermissions: /opt/unetlab/wrappers/unl_wrapper not found")

        print(f"Installed VCP into: {vcp_dest}")
        print(f"Installed VFP into: {vfp_dest}")
    finally:
        if keep_extracted:
            saved_dir = bundle_path.parent / f"extracted-vmx-{version}"
            if saved_dir.exists():
                shutil.rmtree(saved_dir)
            shutil.copytree(temp_dir, saved_dir)
            print(f"Kept extracted contents at: {saved_dir}")
        temp_dir_context.cleanup()


def main() -> int:
    args = parse_args()

    try:
        bundle_path = resolve_bundle_path(args.bundle)
        install_vmx(
            bundle_path=bundle_path,
            eve_root=Path(args.eve_root),
            keep_extracted=args.keep_extracted,
            skip_fixpermissions=args.skip_fixpermissions,
            vfp_metadata_mode=args.vfp_metadata_mode,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
