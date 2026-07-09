"""
Check np.fromfile documentation and behavior specifics.
"""

import numpy as np
import io

# Check numpy version and fromfile signature
print(f"NumPy version: {np.__version__}")

# Check the docstring
print("\n=== np.fromfile docstring ===")
print(np.fromfile.__doc__[:1000])

# Test: Does np.fromfile work with file-like objects?
print("\n=== Test: fromfile with file-like object ===")
try:
    data = io.BytesIO(b'\x00\x00\x80?\x00\x00\x00@\x00\x00@@')  # 1.0, 2.0, 3.0 as floats
    arr = np.fromfile(data, dtype=np.float32, count=3)
    print(f"Read from BytesIO: {arr}")
except Exception as e:
    print(f"Error: {e}")

# Test: Does np.fromfile work with actual file handles?
print("\n=== Test: fromfile with real file handle ===")
import tempfile
with tempfile.NamedTemporaryFile(delete=False) as tmp:
    tmp.write(b'\x00\x00\x80?\x00\x00\x00@\x00\x00@@')
    tmp_path = tmp.name

try:
    with open(tmp_path, 'rb') as f:
        arr = np.fromfile(f, dtype=np.float32, count=3)
        print(f"Read from file handle: {arr}")
finally:
    import os
    os.unlink(tmp_path)

# Test: Buffer behavior
print("\n=== Test: Buffer behavior in Python 3 ===")
import tempfile
with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp:
    # Write ASCII header + binary data
    tmp.write(b"HEADER_LINE_ONE\n")
    tmp.write(b"HEADER_LINE_TWO\n")
    tmp.write(b"END_HEADER\n")
    tmp.write(b'\x00\x00\x80?\x00\x00\x00@\x00\x00@@')
    tmp_path = tmp.name

try:
    with open(tmp_path, 'rb') as f:
        # Simulate readline() header parsing
        while True:
            line = f.readline()
            if b'END_HEADER' in line:
                print(f"Found END_HEADER, file position: {f.tell()}")
                break

        # Now use np.fromfile
        arr = np.fromfile(f, dtype=np.float32, count=3)
        print(f"After readline() -> np.fromfile: {arr}")
        print(f"Expected: [1. 2. 3.]")
        if np.allclose(arr, [1., 2., 3.]):
            print("PASS: Values match")
        else:
            print("FAIL: Values don't match")
finally:
    os.unlink(tmp_path)
