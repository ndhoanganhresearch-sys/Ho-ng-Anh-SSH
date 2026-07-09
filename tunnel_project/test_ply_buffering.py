"""
Test whether PLY binary reader has buffering corruption when using np.fromfile
on a text-mode-prefetched handle after readline() calls.

This tests the specific claim: np.fromfile on a BufferedReader that has been
prefetched by readline() calls will silently skip the buffered bytes and read
from the OS-level file position instead, corrupting the vertex data.
"""

import io
import struct
import tempfile
from pathlib import Path
import numpy as np
import sys

# Manual implementation of the PLY reader to isolate the issue
def read_ply_buffered(fp: str):
    """Reproduce the exact code path from io_layer.py lines 71-105."""
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

        if fmt == "ascii":
            pts = np.empty((n_v, 3), dtype=np.float64)
            for r in range(n_v):
                vs = fh.readline().decode("ascii", "replace").split()
                pts[r] = [float(vs[i]) for i in xyz_i]
        else:
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
            # LINE 102 - The critical line: np.fromfile on buffered handle
            table = np.fromfile(fh, dtype=dtype, count=n_v)
            fn = table.dtype.names or ()
            pts = np.column_stack([table[fn[i]] for i in xyz_i]).astype(np.float64)

    return pts, n_v


def create_binary_ply(fp: str, n_vertices: int = 100):
    """Create a binary little-endian PLY with known vertex data."""
    with open(fp, "wb") as f:
        # Write ASCII header
        header = f"""ply
format binary_little_endian 1.0
element vertex {n_vertices}
property float x
property float y
property float z
end_header
"""
        f.write(header.encode("ascii"))

        # Generate known vertex data
        vertices = []
        for i in range(n_vertices):
            x = float(i) + 0.1
            y = float(i) + 0.2
            z = float(i) + 0.3
            vertices.append((x, y, z))
            f.write(struct.pack("<fff", x, y, z))

    return vertices


def test_ply_buffering_corruption():
    """Test whether buffering causes coordinate corruption."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ply_file = Path(tmpdir) / "test.ply"

        # Create test PLY with 100 vertices
        expected_vertices = create_binary_ply(str(ply_file), n_vertices=100)

        # Read it back using the potentially buggy code path
        try:
            pts, n_v = read_ply_buffered(str(ply_file))
        except Exception as e:
            print(f"FAIL: Exception during read: {e}")
            return False

        print(f"Read {len(pts)} points (expected {len(expected_vertices)})")

        # Check 1: Point count matches
        if len(pts) != len(expected_vertices):
            print(f"FAIL: Point count mismatch. Got {len(pts)}, expected {len(expected_vertices)}")
            return False

        # Check 2: All coordinates match
        max_error = 0.0
        for i, (exp_x, exp_y, exp_z) in enumerate(expected_vertices):
            read_x, read_y, read_z = pts[i]
            error = max(abs(read_x - exp_x), abs(read_y - exp_y), abs(read_z - exp_z))
            if error > 1e-5:  # Float precision tolerance
                print(f"FAIL: Coordinate mismatch at vertex {i}:")
                print(f"  Expected: ({exp_x}, {exp_y}, {exp_z})")
                print(f"  Got:      ({read_x}, {read_y}, {read_z})")
                print(f"  Error:    {error}")
                return False
            max_error = max(max_error, error)

        print(f"PASS: All {len(pts)} coordinates match within {max_error:.2e}")
        return True


if __name__ == "__main__":
    success = test_ply_buffering_corruption()
    sys.exit(0 if success else 1)
