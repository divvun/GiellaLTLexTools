#!/usr/bin/env python3
"""
Poetry build script to ensure pyhfst is installed with Cython optimization.
This script is executed during poetry install and poetry build.
"""

import importlib.util
import subprocess
import sys


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and handle errors."""
    print(f"🔧 {description}")
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def main() -> None:
    """Main build process."""
    print("🚀 Poetry build script: Optimizing pyhfst installation")

    # Check if we need to reinstall pyhfst with Cython
    pyhfst_spec = importlib.util.find_spec("pyhfst")
    if pyhfst_spec is not None:
        print("✅ pyhfst is already installed")

        # Check if Cython is available
        cython_spec = importlib.util.find_spec("Cython")
        if cython_spec is not None:
            print("✅ Cython is available")

            # Force reinstall pyhfst to ensure it uses Cython
            print("🔄 Reinstalling pyhfst with Cython optimization...")
            if not run_command(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "--force-reinstall",
                    "pyhfst",
                    "--no-cache-dir",
                ],
                "Reinstalling pyhfst with Cython",
            ):
                print("⚠️  Warning: Failed to reinstall pyhfst with Cython")
                return

            print("✅ pyhfst reinstalled with Cython optimization")

        else:
            print("⚠️  Cython not available, " "pyhfst performance may be suboptimal")

    else:
        print("ℹ️  pyhfst not yet installed, will be installed by Poetry")

    print("✅ Build script completed successfully")


if __name__ == "__main__":
    main()
