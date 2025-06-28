#!/bin/bash
# Complete CCTNS Copilot Engine Setup Script

echo "🛡️ CCTNS Copilot Engine - Complete Setup"
echo "========================================"

# Check Python version
python_version=$(python3 --version 2>&1)
echo "🐍 Python version: $python_version"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo "❌ Python 3.9+ required"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo "📚 Installing Python packages..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs reports temp models_cache data/exports

# Download models
echo "🤖 Downloading AI models..."
python scripts/download_models.py

# Copy environment file
if [ ! -f .env ]; then
    echo "⚙️ Creating environment file..."
    cp .env.example .env
    echo "📝 Please edit .env with your Oracle connection string"
fi

# Set executable permissions
chmod +x scripts/*.py
chmod +x scripts/*.sh

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 Next steps:"
echo "1. Edit .env file with your Oracle database connection"
echo "2. Run: python run.py"
echo "3. Open: http://localhost:8000"
echo ""
echo "📚 Documentation:"
echo "- API Docs: http://localhost:8000/docs"
echo "- Health Check: http://localhost:8000/api/health"
echo "- Project README: ./README.md"
echo ""
echo "🎯 Happy coding! Build an amazing CCTNS Copilot!"