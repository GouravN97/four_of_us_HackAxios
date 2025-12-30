#!/usr/bin/env python3

try:
    import src.utils.error_handling
    print("Import successful")
    print(dir(src.utils.error_handling))
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()