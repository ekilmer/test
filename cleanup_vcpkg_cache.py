#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
import os
from typing import Dict, List


def get_installed_package_abis(vcpkg_install_path: Path) -> Dict[str, str]:
    """Extract ABI values for all installed packages from the vcpkg status file.

    Args:
        vcpkg_install_path: Path to the vcpkg installation directory

    Returns:
        Dict[str, str]: Dictionary mapping package names to their ABI values
    """
    status_file = vcpkg_install_path / "vcpkg" / "status"
    if not status_file.exists():
        print(f"Error: Status file not found at {status_file}", file=sys.stderr)
        sys.exit(1)

    package_abis: Dict[str, str] = {}
    current_package: str | None = None

    with open(status_file, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("Package: "):
                current_package = line[9:].strip()
            elif line.startswith("Abi: "):
                assert current_package is not None
                package_abis[current_package] = line[5:].strip()

    return package_abis


def collect_and_cleanup_cache(
    binary_cache_path: Path, package_abis: Dict[str, str], dry_run: bool = False
) -> None:
    """Collect all cached ABI files and remove those not matching installed packages.

    Args:
        binary_cache_path: Path to the vcpkg binary cache directory
        package_abis: Dictionary mapping package names to their ABI values
        dry_run: If True, only show what would be removed without making changes
    """
    if not binary_cache_path.exists():
        print(
            f"Error: Binary cache directory '{binary_cache_path}' does not exist",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create a set of all installed ABIs for quick lookup
    installed_abis = set(package_abis.values())

    # Track directories with files to remove and keep
    dirs_with_keep_files = set()
    dirs_with_remove_files = set()

    action = "Would remove" if dry_run else "Removing"

    # Process all cache files
    for file_path in binary_cache_path.rglob("*.zip"):
        parent_dir = file_path.parent
        # Extract the ABI from the filename (remove .zip extension)
        file_abi = file_path.stem
        if file_abi not in installed_abis:
            dirs_with_remove_files.add(parent_dir)
            print(f"{action} {file_path}")
            if not dry_run:
                file_path.unlink()
        else:
            dirs_with_keep_files.add(parent_dir)
            print(f"Keeping {file_path}")

    # Clean up empty directories
    # Only consider directories that had files removed and don't have any files to keep
    dirs_to_check = dirs_with_remove_files - dirs_with_keep_files
    # Sort by depth (deepest first) to ensure we remove from bottom up
    sorted_dirs: List[Path] = sorted(
        dirs_to_check, key=lambda p: len(p.parts), reverse=True
    )
    for dir_path in sorted_dirs:
        try:
            print(f"{action} empty directory: {dir_path}")
            if not dry_run:
                dir_path.rmdir()
        except OSError:
            # Directory not empty or already removed
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup the vcpkg cache directory to only include installed packages"
    )
    parser.add_argument(
        "vcpkg_install_path",
        default=os.getcwd(),
        help="Path to the vcpkg install directory or a directory to search for installed packages. Defaults to the current working directory.",
    )
    parser.add_argument(
        "binary_cache_path",
        help="Path to the vcpkg binary cache directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without making any changes",
    )

    args = parser.parse_args()

    binary_cache_path = Path(args.binary_cache_path)
    vcpkg_install_path = Path(args.vcpkg_install_path)

    # Get ABI values for installed packages
    package_abis = get_installed_package_abis(vcpkg_install_path)
    print("\nInstalled package ABIs:")
    for package, abi in package_abis.items():
        print(f"{package}: {abi}")
    print("")

    # Collect and cleanup cache files
    print(f"Processing binary cache directory: {binary_cache_path}")
    collect_and_cleanup_cache(binary_cache_path, package_abis, args.dry_run)


if __name__ == "__main__":
    main()
