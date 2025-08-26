#!/usr/bin/env python3
"""
Test script for the enhanced OCR CLI
Demonstrates the rich progress visualization features.
"""

import time
from cli import OCRInterface

def demo_progress():
    """Demo the enhanced progress visualization."""
    cli = OCRInterface()
    
    # Show a demo with simulated files
    print("🎬 CLI Enhancement Demo")
    print("=" * 50)
    
    # Test the enhanced menu
    try:
        cli.interactive_menu()
    except KeyboardInterrupt:
        print("\nDemo ended.")

if __name__ == "__main__":
    demo_progress()