"""
Diagnostic test: Show the internal state of the BufferedReader before
and after readline() calls, and track the file descriptor position vs
Python buffer position.

This reveals whether np.fromfile would actually see buffered data.
"""

import struct
import tempfile
from pathlib import Path
import numpy as np
import os

def create_simple_ply(fp: str, n_vertices: int = 10):
    """Create a simple binary PLY."""
    with open(fp, "wb") as f:
        header = f"""ply
format binary_little_endian 1.0
element vertex {n_vertices}
property float x
property float y
property float z
end_header
"""
        f.write(header.encode("ascii"))
        for i in range(n_vertices):
            f.write(struct.pack("<fff", float(i)+0.1, float(i)+0.2, float(i)+0.3))


def test_buffer_state():
    """Show buffer state at critical moments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ply_file = Path(tmpdir) / "test.ply"
        create_simple_ply(str(ply_file), n_vertices=10)

        with open(str(ply_file), "rb") as fh:
            print(f"File opened. Type: {type(fh)}")
            print(f"Is BufferedReader: {hasattr(fh, 'peek')}")

            # Read header line by line
            header_lines = []
            while True:
                before_tell = fh.tell()
                before_fd = os.fstat(fh.fileno()).st_size

                line = fh.readline()

                after_tell = fh.tell()
                if not line:
                    break

                header_lines.append(line)
                text = line.decode("ascii", errors="replace").strip()

                if text == "end_header":
                    print(f"  Found end_header")
                    print(f"    Python tell() before: {before_tell}")
                    print(f"    Python tell() after:  {after_tell}")
                    print(f"    Bytes read: {after_tell - before_tell}")
                    break

            # Now the critical moment: np.fromfile
            print(f"\nBefore np.fromfile:")
            print(f"  fh.tell() = {fh.tell()}")
            print(f"  fh.fileno() = {fh.fileno()}")

            # Peek to see if there's buffered data
            if hasattr(fh, 'peek'):
                peeked = fh.peek(20)
                print(f"  fh.peek(20) = {peeked.hex()}")

            # Read first vertex manually
            raw = fh.read(12)  # 3 floats * 4 bytes
            print(f"\nManual fh.read(12) returned {len(raw)} bytes: {raw.hex()}")

            if len(raw) == 12:
                x, y, z = struct.unpack("<fff", raw)
                print(f"  Decoded as: x={x}, y={y}, z={z}")
                print(f"  Expected:   x=0.1, y=0.2, z=0.3")
                if abs(x - 0.1) < 1e-5 and abs(y - 0.2) < 1e-5 and abs(z - 0.3) < 1e-5:
                    print(f"  MATCH!")
                else:
                    print(f"  MISMATCH!")
            else:
                print(f"  ERROR: Got only {len(raw)} bytes")


if __name__ == "__main__":
    test_buffer_state()
