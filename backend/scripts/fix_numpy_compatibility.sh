#!/bin/bash
# Fix numpy binary incompatibility issues
# This script reinstalls key packages to ensure numpy compatibility

echo "=========================================="
echo "Fixing numpy binary compatibility"
echo "=========================================="
echo ""

# Step 1: Check current numpy version
echo "Step 1: Checking current numpy version..."
python -c "import numpy; print(f'Current numpy: {numpy.__version__}')" || echo "numpy not installed"
echo ""

# Step 2: Uninstall problematic packages
echo "Step 2: Uninstalling packages that may have binary incompatibility..."
pip uninstall -y numpy scipy pandas scikit-learn llama-index-core
echo ""

# Step 3: Reinstall numpy first (latest stable version)
echo "Step 3: Installing numpy (latest stable)..."
pip install --no-cache-dir "numpy>=1.26.0,<2.0.0"
echo ""

# Step 4: Reinstall packages that depend on numpy
echo "Step 4: Reinstalling dependent packages..."
pip install --no-cache-dir scipy pandas scikit-learn
echo ""

# Step 5: Reinstall LlamaIndex packages
echo "Step 5: Reinstalling LlamaIndex packages..."
pip install --no-cache-dir llama-index-core llama-index llama-index-embeddings-openai llama-index-vector-stores-pinecone
echo ""

# Step 6: Verify installation
echo "Step 6: Verifying installation..."
python -c "
import numpy
import pandas
import scipy
from llama_index.core import VectorStoreIndex
print('✓ numpy:', numpy.__version__)
print('✓ pandas:', pandas.__version__)
print('✓ scipy:', scipy.__version__)
print('✓ llama-index-core: OK')
print('')
print('All packages installed successfully!')
"

echo ""
echo "=========================================="
echo "✓ Fix complete! Try running ingestion again:"
echo "  python scripts/ingest_with_llamaparse.py"
echo "=========================================="
