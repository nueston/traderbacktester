# Sparse Checkout Profiles
# 
# This folder contains reusable sparse-checkout profiles for GitHub Actions workflows.
# Each profile defines which files to include/exclude during checkout to optimize
# workflow performance.
#
# Available profiles:
# - minimal: Excludes plotting/demo files (fastest for CI tests)
# - full: Includes all files (for development/comprehensive testing)
# - core: Excludes plotting files and test directory (for building core only)
#
# Usage in workflows:
# - uses: actions/checkout@v3
#   with:
#     sparse-checkout-cone-mode: false
#     sparse-checkout: .github/sparse-checkout/minimal
