import os
import shutil
import tarfile
import sys
import glob

"""
Script to automate Junos testing tasks
Author: Moshiko Nayman
Date: 31/10/2024
Description: This script extracts files, creates folders, moves files around, and deletes the source folder.
Usage: python automate_junos.py <release-version>
"""

def extract_and_move_files(release_version):
    tarball = f"vmx-bundle-{release_version}.tgz"
    extract_path = "vmx"
    
    # Extract the tarball
    with tarfile.open(tarball, "r:gz") as tar:
        tar.extractall()
    
    # Define source and destination paths
    src_dir = os.path.join(extract_path, "images")
    vcp_dest = f"/opt/unetlab/addons/qemu/vmxvcp-{release_version}-domestic-VCP"
    vfp_dest = f"/opt/unetlab/addons/qemu/vmxvfp-{release_version}-domestic-VFP"
    
    # Create destination directories
    os.makedirs(vcp_dest, exist_ok=True)
    os.makedirs(vfp_dest, exist_ok=True)
    
    # Move files to the respective directories
    shutil.copy(os.path.join(src_dir, f"junos-vmx-x86-64-{release_version}.qcow2"), os.path.join(vcp_dest, "virtioa.qcow2"))
    shutil.copy(os.path.join(src_dir, "vmxhdd.img"), os.path.join(vcp_dest, "virtiob.qcow2"))
    shutil.copy(os.path.join(src_dir, "metadata-usb-re.img"), os.path.join(vcp_dest, "virtioc.qcow2"))
    
    # Find the vFPC image file and copy it
    vfp_image = glob.glob(os.path.join(src_dir, "vFPC-*.img"))[0]
    shutil.copy(vfp_image, os.path.join(vfp_dest, "virtioa.qcow2"))
    
    # Clean up
    shutil.rmtree(extract_path)
    print(f"Process completed for release version {release_version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python automate_junos.py <release-version>")
        sys.exit(1)
    
    release_version = sys.argv[1]
    extract_and_move_files(release_version)
