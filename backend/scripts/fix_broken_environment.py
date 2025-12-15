"""Emergency fix for completely broken Python environment.

This handles cases where numpy is so corrupted it doesn't have __version__.

Usage:
    python scripts/fix_broken_environment.py
"""

import subprocess
import sys
import os


def run_command(cmd: list[str], description: str, ignore_errors=False):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 and not ignore_errors:
            print(f"⚠️  Command had errors (may be expected):")
            if result.stderr:
                print(result.stderr[:500])
        else:
            print(f"✓ {description} complete")
        if result.stdout and "Successfully" in result.stdout:
            print(result.stdout)
        return True
    except Exception as e:
        if not ignore_errors:
            print(f"❌ {description} failed: {e}")
        return False


def detect_environment():
    """Detect if we're in conda or venv."""
    is_conda = os.path.exists(os.path.join(sys.prefix, 'conda-meta'))
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', '')

    print("\n" + "="*80)
    print("ENVIRONMENT DETECTION")
    print("="*80)
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Is Conda: {is_conda}")
    if is_conda:
        print(f"Conda environment: {conda_env}")
    print("="*80)

    return is_conda, conda_env


def fix_with_conda():
    """Fix using conda package manager."""
    print("\n" + "="*80)
    print("FIXING WITH CONDA")
    print("="*80)

    print("\n⚠️  WARNING: You're in the conda 'base' environment.")
    print("It's recommended to create a dedicated environment instead.")
    print("\nRecommended approach:")
    print("  conda create -n diabetes-fyp python=3.11")
    print("  conda activate diabetes-fyp")
    print("  pip install -r requirements.txt")
    print("\nPress Enter to continue with base environment fix, or Ctrl+C to stop...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nAborted by user. Create a new conda environment first.")
        return False

    # Remove broken packages
    print("\nStep 1: Removing broken packages with conda...")
    packages = ["numpy", "pandas", "scipy", "scikit-learn"]
    for pkg in packages:
        run_command(
            ["conda", "remove", "-y", pkg],
            f"Removing {pkg}",
            ignore_errors=True
        )

    # Also remove pip packages
    print("\nStep 2: Removing pip-installed versions...")
    for pkg in packages + ["llama-index-core", "llama-index"]:
        run_command(
            [sys.executable, "-m", "pip", "uninstall", "-y", pkg],
            f"Removing pip {pkg}",
            ignore_errors=True
        )

    # Install numpy with conda first
    print("\nStep 3: Installing numpy with conda...")
    if not run_command(
        ["conda", "install", "-y", "numpy"],
        "Installing numpy via conda"
    ):
        return False

    # Install other scientific packages with conda
    print("\nStep 4: Installing scientific packages with conda...")
    for pkg in ["pandas", "scipy", "scikit-learn"]:
        run_command(
            ["conda", "install", "-y", pkg],
            f"Installing {pkg} via conda",
            ignore_errors=False
        )

    # Install llama-index with pip
    print("\nStep 5: Installing LlamaIndex packages with pip...")
    llama_packages = [
        "llama-parse",
        "llama-index-core",
        "llama-index",
        "llama-index-embeddings-openai",
        "llama-index-vector-stores-pinecone",
    ]
    for pkg in llama_packages:
        run_command(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", pkg],
            f"Installing {pkg}",
            ignore_errors=False
        )

    return True


def fix_with_pip():
    """Fix using pip package manager."""
    print("\n" + "="*80)
    print("FIXING WITH PIP")
    print("="*80)

    # Force remove all packages
    print("\nStep 1: Force removing all packages...")
    packages = [
        "numpy", "pandas", "scipy", "scikit-learn",
        "llama-index-core", "llama-index", "llama-parse",
        "llama-index-embeddings-openai", "llama-index-vector-stores-pinecone"
    ]

    for pkg in packages:
        run_command(
            [sys.executable, "-m", "pip", "uninstall", "-y", pkg],
            f"Uninstalling {pkg}",
            ignore_errors=True
        )

    # Clear pip cache
    print("\nStep 2: Clearing pip cache...")
    run_command(
        [sys.executable, "-m", "pip", "cache", "purge"],
        "Clearing pip cache",
        ignore_errors=True
    )

    # Install numpy first
    print("\nStep 3: Installing numpy from scratch...")
    if not run_command(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--force-reinstall", "numpy==1.26.4"],
        "Installing numpy 1.26.4"
    ):
        return False

    # Install scientific packages
    print("\nStep 4: Installing scientific packages...")
    for pkg in ["scipy", "pandas", "scikit-learn"]:
        run_command(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--force-reinstall", pkg],
            f"Installing {pkg}",
            ignore_errors=False
        )

    # Install LlamaIndex packages
    print("\nStep 5: Installing LlamaIndex packages...")
    llama_packages = [
        "llama-parse",
        "llama-index-core",
        "llama-index",
        "llama-index-embeddings-openai",
        "llama-index-vector-stores-pinecone",
    ]
    for pkg in llama_packages:
        run_command(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", pkg],
            f"Installing {pkg}",
            ignore_errors=False
        )

    return True


def verify_installation():
    """Verify that packages are working."""
    print("\n" + "="*80)
    print("VERIFYING INSTALLATION")
    print("="*80)

    # Test imports one by one
    tests = [
        ("numpy", "import numpy; print(f'numpy: {numpy.__version__}')"),
        ("pandas", "import pandas; print(f'pandas: {pandas.__version__}')"),
        ("scipy", "import scipy; print(f'scipy: {scipy.__version__}')"),
        ("llama-index-core", "from llama_index.core import VectorStoreIndex; print('llama-index-core: OK')"),
    ]

    all_passed = True
    for name, test_code in tests:
        try:
            result = subprocess.run(
                [sys.executable, "-c", test_code],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"✓ {result.stdout.strip()}")
            else:
                print(f"❌ {name} failed: {result.stderr[:200]}")
                all_passed = False
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            all_passed = False

    return all_passed


def main():
    """Main fix routine."""
    print("="*80)
    print("EMERGENCY FIX FOR BROKEN PYTHON ENVIRONMENT")
    print("="*80)
    print("\nThis script will completely reinstall numpy and related packages.")

    # Detect environment
    is_conda, conda_env = detect_environment()

    # Choose fix strategy
    if is_conda:
        print("\n⚠️  Conda environment detected.")
        print("\nChoose fix strategy:")
        print("  1. Fix with conda (recommended for conda environments)")
        print("  2. Fix with pip only")
        print("  3. Exit and create new environment (safest)")

        choice = input("\nEnter choice (1/2/3): ").strip()

        if choice == "3":
            print("\n" + "="*80)
            print("RECOMMENDED: Create a fresh conda environment")
            print("="*80)
            print("\nRun these commands:")
            print("  conda create -n diabetes-fyp python=3.11")
            print("  conda activate diabetes-fyp")
            print("  cd backend")
            print("  pip install -r requirements.txt")
            print("\nThen test with:")
            print("  python scripts/test_llamaparse.py")
            return False
        elif choice == "1":
            success = fix_with_conda()
        else:
            success = fix_with_pip()
    else:
        success = fix_with_pip()

    if not success:
        print("\n❌ Fix failed. See errors above.")
        return False

    # Verify
    if verify_installation():
        print("\n" + "="*80)
        print("✓ ALL PACKAGES FIXED AND VERIFIED")
        print("="*80)
        print("\nYou can now run:")
        print("  python scripts/ingest_with_llamaparse.py")
        print("\nOr test first:")
        print("  python scripts/test_llamaparse.py")
        return True
    else:
        print("\n" + "="*80)
        print("❌ VERIFICATION FAILED")
        print("="*80)
        print("\nSome packages still have issues.")
        print("\nRECOMMENDED: Create a fresh environment:")
        print("  conda create -n diabetes-fyp python=3.11")
        print("  conda activate diabetes-fyp")
        print("  pip install -r requirements.txt")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
