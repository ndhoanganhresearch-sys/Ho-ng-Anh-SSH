"""
More aggressive test: Create a PLY with a large ASCII header (to trigger
buffering across the boundary) and many vertices.

The hypothesis is that when readline() is called many times on a BufferedReader,
it prefetches large chunks (typically 8KB), and if the binary vertex data starts
just after the header, np.fromfile may not see the prefetched bytes.
"""

import struct
import tempfile
from pathlib import Path
import numpy as np
import sys

def read_ply_buffered(fp: str):
    """Reproduce the exact code path from io_layer.py."""
    path = Path(fp)
    with path.open("rb") as fh:
        if fh.readline().strip() != b"ply":
            raise ValueError(f"Not PLY: {fp}")
        fmt = None
        n_v = 0
        props = []
        elem = None
        while True:
            raw = fh.readline()
            if not raw:
                raise ValueError("PLY header truncated.")
            line = raw.decode("ascii", errors="replace").strip()
            if line == "end_header":
                break
            if not line or line.startswith("comment"):
                continue
            p = line.split()
            if p[0] == "format":
                fmt = p[1]
            elif p[0] == "element":
                elem = p[1]
                n_v = int(p[2]) if elem == "vertex" else n_v
            elif p[0] == "property" and elem == "vertex":
                props.append((p[2], p[1]))

        pnames = [nm.lower() for nm, _ in props]
        xyz_i = [pnames.index(a) for a in ("x", "y", "z")]

        if fmt != "ascii":
            PLY_DTYPES = {
                "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
                "short": "i2", "int16": "i2", "ushort": "u2", "uint16": "u2",
                "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
                "float": "f4", "float32": "f4", "double": "f8",
            }
            endian = "<" if "little" in (fmt or "") else ">"
            dtype = np.dtype(
                [(f"f{i}_{nm}", endian + PLY_DTYPES[k]) for i, (nm, k) in enumerate(props)]
            )
            # LINE 102 - The critical line
            table = np.fromfile(fh, dtype=dtype, count=n_v)
            fn = table.dtype.names or ()
            pts = np.column_stack([table[fn[i]] for i in xyz_i]).astype(np.float64)
        else:
            raise ValueError("Unexpected ASCII format in this test")

    return pts, n_v


def create_ply_with_large_header(fp: str, n_vertices: int = 1000, header_lines: int = 200):
    """
    Create a binary PLY with a large header (many comment lines) to trigger
    buffering across the boundary between header and binary data.
    """
    with open(fp, "wb") as f:
        # Start header
        f.write(b"ply\n")
        f.write(b"format binary_little_endian 1.0\n")

        # Add many comment lines to force buffering
        for i in range(header_lines):
            comment = f"comment This is comment line {i}: " + "X" * 50 + "\n"
            f.write(comment.encode("ascii"))

        # Element definition
        f.write(f"element vertex {n_vertices}\n".encode("ascii"))
        f.write(b"property float x\n")
        f.write(b"property float y\n")
        f.write(b"property float z\n")
        f.write(b"end_header\n")

        # Now write binary vertex data
        expected_vertices = []
        for i in range(n_vertices):
            x = float(i) + 0.111
            y = float(i) + 0.222
            z = float(i) + 0.333
            expected_vertices.append((x, y, z))
            f.write(struct.pack("<fff", x, y, z))

    return expected_vertices


def test_large_header():
    """Test PLY reading with large header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ply_file = Path(tmpdir) / "test_large.ply"

        expected = create_ply_with_large_header(str(ply_file), n_vertices=1000, header_lines=200)

        try:
            pts, n_v = read_ply_buffered(str(ply_file))
        except Exception as e:
            print(f"FAIL: Exception during read: {e}")
            import traceback
            traceback.print_exc()
            return False

        print(f"Read {len(pts)} points (expected {len(expected)})")

        if len(pts) != len(expected):
            print(f"FAIL: Point count mismatch. Got {len(pts)}, expected {len(expected)}")
            # Check if we got truncated data
            print(f"First 5 expected points:")
            for i in range(min(5, len(expected))):
                print(f"  {i}: {expected[i]}")
            print(f"First 5 read points:")
            for i in range(min(5, len(pts))):
                print(f"  {i}: {pts[i]}")
            return False

        # Spot-check random vertices
        errors = []
        for i in [0, 100, 500, 999]:
            if i < len(expected) and i < len(pts):
                exp_x, exp_y, exp_z = expected[i]
                read_x, read_y, read_z = pts[i]
                error = max(abs(read_x - exp_x), abs(read_y - exp_y), abs(read_z - exp_z))
                if error > 1e-4:
                    errors.append(f"Vertex {i}: exp={expected[i]}, got={pts[i]}, err={error}")

        if errors:
            print(f"FAIL: Coordinate mismatches:")
            for e in errors:
                print(f"  {e}")
            return False

        print(f"PASS: All {len(pts)} coordinates match")
        return True


if __name__ == "__main__":
    success = test_large_header()
    sys.exit(0 if success else 1)
