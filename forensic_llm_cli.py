#!/usr/bin/env python3
"""
Forensic-LLM Command Line Interface
This wrapper ensures the correct paths are set up before running the main script.
"""

import sys
import os
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()

# Add the Extractor directory to Python path
extractor_dir = script_dir / "Extractor"
sys.path.insert(0, str(extractor_dir))

# Change to the Extractor directory
os.chdir(extractor_dir)

# Now import and run the main function
def main():
    """Main entry point for forensic-llm command"""
    # Import here to ensure we're in the right directory and path is set
    import browse_scraper
    browse_scraper.main()

if __name__ == "__main__":
    main()

