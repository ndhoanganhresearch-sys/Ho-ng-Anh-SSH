"""
Direct test of np.fromfile behavior with BufferedReader after readline() calls.

Tests the exact scenario: After calling readline() multiple times on a BufferedReader,
does np.fromfile correctly read from the buffered position, or does it skip buffered
bytes?
"""

import struct
import tempfile
from pathlib import Path
import numpy as np

def create_ply_with_header_boundary(fp: str, n_vertices: int = 10):
    """
    Create a PLY where the boundary between header and binary data
    is specifically designed to test buffering. The header is crafted
    so that the 'end_header' line does NOT fall on an 8KB boundary,
    forcing some buffered bytes to remain after readline() returns.
    """
    with open(fp, "wb") as f:
        # Build header piece by piece
        header_parts = [
            b"ply\n",
            b"format binary_little_endian 1.0\n",
        ]

        # Pad with comments to position end_header awkwardly in the buffer
        # Default buffer is usually 8192 bytes; we want end_header to be
        # partway through a buffer load
        for i in range(50):
            header_parts.append(f"comment Line {i:03d}: {'A' * 100}\n".encode("ascii"))

        header_parts.extend([
            f"element vertex {n_vertices}\n".encode("ascii"),
            b"property float x\n",
            b"property float y\n",
            b"property float z\n",
            b"end_header\n",
        ])

        header = b"".join(header_parts)
        f.write(header)

        # Write binary data
        for i in range(n_vertices):
            x = float(i) + 0.111
            y = float(i) + 0.222
            z = float(i) + 0.333
            f.write(struct.pack("<fff", x, y, z))

    print(f"Created PLY: {len(header)} bytes header, {12 * n_vertices} bytes binary data")
    return n_vertices


def test_np_fromfile_after_readline():
    """Test np.fromfile directly after readline() calls."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ply_file = Path(tmpdir) / "test.ply"
        n_vertices = create_ply_with_header_boundary(str(ply_file), n_vertices=10)

        # Open and read header
        with open(str(ply_file), "rb") as fh:
            print(f"\n=== Reading header ===")
            lines_read = 0
            while True:
                line = fh.readline()
                lines_read += 1
                if line.decode("ascii", errors="replace").strip() == "end_header":
                    print(f"Read {lines_read} header lines")
                    print(f"Current position: {fh.tell()}")
                    break

            print(f"\n=== Using np.fromfile ===")
            # This is the exact pattern from io_layer.py line 102
            dtype = np.dtype([
                ("f0_x", "<f4"),
                ("f1_y", "<f4"),
                ("f2_z", "<f4"),
            ])

            print(f"Before np.fromfile: fh.tell() = {fh.tell()}")
            table = np.fromfile(fh, dtype=dtype, count=n_vertices)
            print(f"After np.fromfile: fh.tell() = {fh.tell()}")
            print(f"Read {len(table)} records")

            # Extract and verify
            pts = np.column_stack([table[f"f{i}_{c}"] for i, c in enumerate(["x", "y", "z"])])
            print(f"\n=== Verification ===")
            print(f"First vertex: {pts[0]} (expected: [0.111, 0.222, 0.333])")
            print(f"Last vertex: {pts[-1]} (expected: [9.111, 9.222, 9.333])")

            # Check for corruption
            all_match = True
            for i in range(n_vertices):
                exp_x, exp_y, exp_z = float(i) + 0.111, float(i) + 0.222, float(i) + 0.333
                got_x, got_y, got_z = pts[i]
                if abs(got_x - exp_x) > 1e-4 or abs(got_y - exp_y) > 1e-4 or abs(got_z - exp_z) > 1e-4:
                    print(f"MISMATCH at vertex {i}: got {pts[i]}, expected [{exp_x}, {exp_y}, {exp_z}]")
                    all_match = False
                    if i < 3:  # Print details for first few mismatches
                        print(f"  Raw hex: {struct.pack('<fff', got_x, got_y, got_z).hex()}")

            if all_match:
                print(f"PASS: All {n_vertices} vertices match expected values")
            else:
                print(f"FAIL: Some vertices don't match")

            return all_match


if __name__ == "__main__":
    import sys
    success = test_np_fromfile_after_readline()
    sys.exit(0 if success else 1)
