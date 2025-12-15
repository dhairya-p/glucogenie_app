"""Fix numpy binary incompatibility issues.

This script reinstalls key packages to ensure numpy compatibility.
Run this if you see: "numpy.dtype size changed, may indicate binary incompatibility"

Usage:
    python scripts/fix_numpy_compatibility.py
"""

import subprocess
import sys


def run_command(cmd: list[str], description: str):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ {description} complete")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(e.stderr)
        return False


def main():
    """Main fix routine."""
    print("=" * 80)
    print("FIXING NUMPY BINARY INCOMPATIBILITY")
    print("=" * 80)

    # Step 1: Check current numpy version
    print("\nStep 1: Checking current numpy version...")
    try:
        import numpy
        print(f"  Current numpy: {numpy.__version__}")
    except ImportError:
        print("  numpy not installed")

    # Step 2: Uninstall problematic packages
    print("\nStep 2: Uninstalling packages with potential binary incompatibility...")
    packages_to_remove = [
        "numpy",
        "scipy",
        "pandas",
        "scikit-learn",
        "llama-index-core",
        "llama-index",
    ]

    for package in packages_to_remove:
        run_command(
            [sys.executable, "-m", "pip", "uninstall", "-y", package],
            f"Uninstalling {package}"
        )

    # Step 3: Reinstall numpy first
    print("\nStep 3: Installing numpy (latest stable)...")
    if not run_command(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "numpy>=1.26.0,<2.0.0"],
        "Installing numpy"
    ):
        print("Failed to install numpy. Exiting.")
        return False

    # Step 4: Reinstall scipy, pandas, scikit-learn
    print("\nStep 4: Reinstalling packages that depend on numpy...")
    dependencies = ["scipy", "pandas", "scikit-learn"]

    for dep in dependencies:
        if not run_command(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", dep],
            f"Installing {dep}"
        ):
            print(f"Warning: Failed to install {dep}")

    # Step 5: Reinstall LlamaIndex packages
    print("\nStep 5: Reinstalling LlamaIndex packages...")
    llama_packages = [
        "llama-index-core",
        "llama-index",
        "llama-index-embeddings-openai",
        "llama-index-vector-stores-pinecone",
    ]

    for package in llama_packages:
        if not run_command(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", package],
            f"Installing {package}"
        ):
            print(f"Warning: Failed to install {package}")

    # Step 6: Verify installation
    print("\nStep 6: Verifying installation...")
    print("=" * 80)

    try:
        import numpy
        import pandas
        import scipy
        from llama_index.core import VectorStoreIndex

        print("✓ numpy:", numpy.__version__)
        print("✓ pandas:", pandas.__version__)
        print("✓ scipy:", scipy.__version__)
        print("✓ llama-index-core: OK")
        print("\n✓ All packages installed successfully!")
        print("=" * 80)
        print("\nYou can now run ingestion:")
        print("  python scripts/ingest_with_llamaparse.py")
        print("=" * 80)
        return True

    except ImportError as e:
        print(f"❌ Verification failed: {e}")
        print("\nSome packages may not have installed correctly.")
        print("Try running this script again or install manually:")
        print("  pip install numpy scipy pandas llama-index-core")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
