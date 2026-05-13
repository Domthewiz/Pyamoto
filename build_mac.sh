#!/bin/bash
# Build Pyamoto for macOS
echo "Building for macOS using universal_venv..."
./universal_venv/bin/python build.py bdist_mac
echo "Build complete. Check build/Pyamoto.app"
