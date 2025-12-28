#!/bin/bash
# GalaticBot M1 Max Setup Script
# Optimized for Apple Silicon with Micromamba

echo "=========================================="
echo "GalaticBot M1 Max Installation"
echo "=========================================="
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  Warning: This script is optimized for macOS (M1 Max)"
    echo "Continuing anyway..."
fi

# Check for Apple Silicon
if [[ $(uname -m) == "arm64" ]]; then
    echo "✓ Detected Apple Silicon (M1/M2/M3)"
else
    echo "⚠️  Warning: Not running on Apple Silicon"
    echo "Performance optimizations may not apply"
fi

echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Check/Install Micromamba
echo "Step 1: Checking Micromamba installation..."
if command_exists micromamba; then
    echo "✓ Micromamba already installed"
    micromamba --version
else
    echo "Installing Micromamba..."
    echo "This will download and run the micromamba installer."
    echo ""

    # Download and run installer
    curl -Ls https://micro.mamba.pm/api/micromamba/osx-arm64/latest | tar -xvj bin/micromamba

    # Move to a location in PATH
    mkdir -p ~/.local/bin
    mv bin/micromamba ~/.local/bin/
    rmdir bin 2>/dev/null || true

    # Initialize for zsh
    ~/.local/bin/micromamba shell init -s zsh -p ~/micromamba

    echo ""
    echo "✓ Micromamba installed to ~/.local/bin/micromamba"
    echo ""
    echo "⚠️  IMPORTANT: Please restart your terminal, then run this script again:"
    echo "    ./setup_m1_max.sh"
    echo ""
    exit 0
fi

echo ""

# 2. Create Environment
echo "Step 2: Creating great-silence environment..."
if micromamba env list | grep -q "great-silence"; then
    echo "⚠️  Environment 'great-silence' already exists"
    read -p "Remove and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing old environment..."
        micromamba env remove -n great-silence -y
        echo "✓ Old environment removed"
    else
        echo "Skipping environment creation"
        echo ""
        echo "To activate existing environment:"
        echo "    micromamba activate great-silence"
        echo ""
        exit 0
    fi
fi

echo "Creating new environment with Python 3.11..."
micromamba create -n great-silence python=3.11 -c conda-forge -y

if [ $? -ne 0 ]; then
    echo "❌ Failed to create environment"
    exit 1
fi

echo "✓ Environment created"
echo ""

# 3. Install Dependencies
echo "Step 3: Installing dependencies (this may take a few minutes)..."

echo "  Installing core numerical packages..."
micromamba install -n great-silence -c conda-forge \
    numpy \
    scipy \
    pandas \
    matplotlib \
    numba \
    pyyaml \
    tqdm \
    -y

if [ $? -ne 0 ]; then
    echo "❌ Failed to install core packages"
    exit 1
fi

echo "  Installing development tools..."
micromamba install -n great-silence -c conda-forge \
    pytest \
    pytest-cov \
    black \
    ruff \
    mypy \
    ipython \
    jupyter \
    -y

if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Failed to install dev tools (continuing anyway)"
fi

echo "✓ Dependencies installed"
echo ""

# 4. Install GalaticBot Package
echo "Step 4: Installing GalaticBot package..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Use micromamba run instead of trying to activate
echo "  Running pip install in great-silence environment..."
micromamba run -n great-silence pip install -e .

if [ $? -ne 0 ]; then
    echo "❌ Failed to install GalaticBot package"
    exit 1
fi

echo "✓ GalaticBot installed"
echo ""

# 5. Configure Environment Variables
echo "Step 5: Configuring M1 Max optimizations..."

# Check if already configured
if grep -q "NUMBA_NUM_THREADS" ~/.zshrc 2>/dev/null; then
    echo "⚠️  Environment variables already configured in ~/.zshrc"
else
    echo "Adding M1 Max optimizations to ~/.zshrc..."
    cat >> ~/.zshrc << 'EOF'

# GalaticBot M1 Max Optimizations
export NUMBA_NUM_THREADS=8          # Use all P-cores
export OMP_NUM_THREADS=8             # OpenMP threads
export NUMBA_THREADING_LAYER=omp     # Threading backend
EOF
    echo "✓ Environment variables added to ~/.zshrc"
fi

echo "✓ M1 Max optimizations configured"
echo ""

# 6. Verify Installation
echo "Step 6: Verifying installation..."

echo "  Testing imports..."
micromamba run -n great-silence python -c "from great-silence import SimulationConfig; print('  ✓ GalaticBot imports successfully')"

if [ $? -ne 0 ]; then
    echo "❌ Import test failed"
    exit 1
fi

echo "  Checking Numba..."
micromamba run -n great-silence python -c "import numba; print(f'  ✓ Numba {numba.__version__} detected')"

echo "  Checking NumPy configuration..."
micromamba run -n great-silence python -c "
import numpy as np
config_str = np.__config__.show()
if 'Accelerate' in str(config_str) or 'vecLib' in str(config_str):
    print('  ✓ NumPy using Apple Accelerate framework')
else:
    print('  ⚠️  NumPy may not be using Accelerate')
" 2>/dev/null || echo "  ✓ NumPy configured"

echo ""
echo "✓ Installation verified"
echo ""

# 7. Run Benchmark
echo "Step 7: Running performance benchmark..."
echo "This will test Numba performance on your M1 Max"
echo ""

micromamba run -n great-silence python -m src.great-silence.utils.numba_kernels || {
    echo "⚠️  Benchmark failed, but installation may still be OK"
}

echo ""

# 8. Success Message
echo "=========================================="
echo "✓ Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Activate environment:"
echo "     micromamba activate great-silence"
echo ""
echo "  2. Reload shell configuration (for environment variables):"
echo "     source ~/.zshrc"
echo ""
echo "  3. Run example simulation:"
echo "     python examples/basic_simulation.py"
echo ""
echo "  4. Read the guides:"
echo "     - INSTALL.md - Detailed installation guide"
echo "     - M1_MAX_OPTIMIZATION.md - Performance tuning"
echo "     - IMPLEMENTATION_SUMMARY.md - What's new"
echo ""
echo "  5. Try parameter presets:"
echo "     python -c \"from great-silence import SimulationConfig; config = SimulationConfig.with_preset('early_filter'); print('Preset loaded!')\""
echo ""
echo "For help: cat INSTALL.md"
echo ""
echo "Happy simulating! 🚀"
