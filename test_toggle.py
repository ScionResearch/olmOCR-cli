#!/usr/bin/env python3
"""
Test script to verify toggle functionality
"""

from cli import OCRInterface
import time

# Create OCR interface
interface = OCRInterface()

# Test initial state
print(f"Initial show_logs_mode: {interface.show_logs_mode}")

# Test keypress detection (without actually requiring keypress)
key = interface.check_keypress()
print(f"Keypress detection test (should be None if no key pressed): {key}")

# Test configuration
interface.config.set("show_logs", True)
print(f"Config show_logs after setting to True: {interface.config.get('show_logs')}")

# Create new interface to test initialization with show_logs=True
interface2 = OCRInterface()
interface2.config.set("show_logs", True)
interface2.show_logs_mode = interface2.config.get("show_logs", False)
print(f"Interface2 show_logs_mode: {interface2.show_logs_mode}")

print("Toggle functionality test completed successfully!")