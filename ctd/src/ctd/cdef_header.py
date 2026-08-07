import re
from pathlib import Path


def load_cdef_header(path: str | Path) -> str:
    """Load and transform a dual-use API header for ``FFI.cdef()``."""
    header_path = Path(path)
    declarations = header_path.read_text(encoding="utf-8")

    # Remove indiscriminately C-preprocessor directives from a dual-use API header.
    declarations = re.sub(
        r"^[ \t]*#[ \t]*(?:if|ifdef|ifndef|endif|define)\b.*(?:\r?\n|$)",
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
    declarations = re.sub(
        r"^[A-Z][A-Z0-9_]*_API[ \t]+",
        "",
        declarations,
        flags=re.MULTILINE,
    )

    return declarations
