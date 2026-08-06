import re
from pathlib import Path


def transform_cdef_header(header_name: str, declarations: str) -> str:
    """Remove the C-only wrapper syntax from a dual-use API header."""
    guard = re.sub(r"[^A-Za-z0-9]", "_", header_name).upper()
    escaped_guard = re.escape(guard)

    declarations = re.sub(
        rf"^[ \t]*#[ \t]*ifndef[ \t]+{escaped_guard}[ \t]*(?:\r?\n|$)",
        "",
        declarations,
        flags=re.MULTILINE,
    )
    declarations = re.sub(
        rf"^[ \t]*#[ \t]*define[ \t]+{escaped_guard}[ \t]*(?:\r?\n|$)",
        "",
        declarations,
        flags=re.MULTILINE,
    )
    declarations = re.sub(
        rf"^[ \t]*#[ \t]*endif"
        rf"(?:[ \t]*/\*[ \t]*{escaped_guard}[ \t]*\*/)?"
        rf"[ \t]*(?:\r?\n|$)",
        "",
        declarations,
        flags=re.MULTILINE,
    )
    declarations = re.sub(
        r"^CTD_DATA_API[ \t]+",
        "extern ",
        declarations,
        flags=re.MULTILINE,
    )
    return re.sub(
        r"^[A-Z][A-Z0-9_]*_API[ \t]+",
        "",
        declarations,
        flags=re.MULTILINE,
    )


def load_cdef_header(path: str | Path) -> str:
    """Load and transform a dual-use API header for ``FFI.cdef()``."""
    header_path = Path(path)
    declarations = header_path.read_text(encoding="utf-8")
    return transform_cdef_header(header_path.name, declarations)
