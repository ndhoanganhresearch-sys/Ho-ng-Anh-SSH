"""
Verify how np.fromfile handles file objects by examining its actual behavior.

The claim says that np.fromfile reads from the OS-level file descriptor
(bypassing Python's buffer). Let's test if that's actually what happens.
"""

import numpy as np
import tempfile
import struct
import os

def test_fromfile_uses_seek_tell():
    """
    If np.fromfile uses the file descriptor directly (os-level read()),
    it would ignore the Python buffer and seek position.

    If np.fromfile uses tell() and seek(), it respects Python buffering.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp:
        # Write structured data: header + binary payload
        tmp.write(b"MAGIC_MARKER\n")  # 13 bytes
        tmp.write(b"3 floats follow\n")  # 16 bytes
        # Total header: 29 bytes

        # Binary payload: 3 floats (12 bytes)
        payload = struct.pack("<fff", 1.0, 2.0, 3.0)
        tmp.write(payload)
        tmp_path = tmp.name

    try:
        with open(tmp_path, 'rb') as f:
            # Read header via readline (text mode style)
            while True:
                line = f.readline()
                if b"3 floats follow" in line:
                    break

            print(f"After readline(), file position: {f.tell()}")

            # The question: Will np.fromfile respect the tell() position?
            arr = np.fromfile(f, dtype=np.float32, count=3)

            print(f"np.fromfile returned: {arr}")
            print(f"Expected: [1. 2. 3.]")

            if np.allclose(arr, [1., 2., 3.]):
                print("[PASS] np.fromfile respected the file position (uses tell/seek)")
                return True
            else:
                print("[FAIL] np.fromfile did NOT respect position (reads from OS fd)")
                return False
    finally:
        import os
        os.unlink(tmp_path)


def test_mixed_io():
    """
    More complex test: mix readline() and np.fromfile to ensure
    they coordinate correctly.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp:
        # Structured data with header and multiple records
        tmp.write(b"RECORD_TYPE: FLOATS\n")
        tmp.write(b"COUNT: 5\n")
        tmp.write(b"END_METADATA\n")

        # 5 records of (int, float) pairs
        for i in range(5):
            tmp.write(struct.pack("<if", i, float(i) * 1.5))

        tmp_path = tmp.name

    try:
        with open(tmp_path, 'rb') as f:
            # Parse metadata via readline
            while True:
                line = f.readline()
                if b"END_METADATA" in line:
                    break

            print(f"\nAfter readline metadata, file position: {f.tell()}")

            # Read structured binary with np.fromfile
            dtype = np.dtype([("id", "<i4"), ("value", "<f4")])
            records = np.fromfile(f, dtype=dtype, count=5)

            print(f"Read {len(records)} records")
            print(f"IDs: {records['id']}")
            print(f"Values: {records['value']}")

            expected_ids = np.array([0, 1, 2, 3, 4])
            expected_vals = np.array([0., 1.5, 3., 4.5, 6.])

            if np.array_equal(records['id'], expected_ids) and np.allclose(records['value'], expected_vals):
                print("[PASS] Mixed readline() + np.fromfile works correctly")
                return True
            else:
                print("[FAIL] Data corruption in mixed IO")
                return False
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    import sys
    result1 = test_fromfile_uses_seek_tell()
    result2 = test_mixed_io()
    sys.exit(0 if (result1 and result2) else 1)
