# Testing C with Pytest and CFFI

This repository explores using [CFFI](https://cffi.readthedocs.io/) API mode as
a bridge from Pytest to a small C library named **CTD**. CTD deliberately
contains scalars, strings, structures, arrays, pointers, global state, allocated
memory, and functions that normally have internal linkage. The examples are
small so that the C/Python boundary, rather than application logic, remains the
focus.

The repository preserves two alternative wrapper workflows:

1. build CTD as a standalone shared library and dynamically link the generated
   CFFI extension to it; or
2. compile `ctd.c` as part of the generated CFFI extension, embedding the CTD
   implementation in that extension.

Both workflows produce an extension with the same import name,
`_ctd_wrapper`. The ordinary tests intentionally exercise that common Python
interface and do not know which workflow produced the extension.

## Repository layout

The principal implementation is in `ctd/src/ctd/`:

- `ctd_api.h` contains declarations exposed through CFFI.
- `ctd.h` is the C developer header and includes `ctd_api.h`.
- `ctd.c` implements CTD.
- `cdef_header.py` mechanically converts the dual-use API header to CDEF text.
- `build_ctd.py` builds standalone static and shared CTD libraries.
- `build_ctd_wrapper.py` builds the dynamically linked CFFI wrapper only.
- `build_ctd_wrapper_embedded.py` builds the wrapper with `ctd.c` embedded.
- `ctd_demo.py` demonstrates calls through the built wrapper.
- `ctd_introspect.py` and `introspect/` inspect CFFI's declaration model.

The Pytest suite is in `ctd/tests/`. Project dependencies and test discovery
configuration are in `pyproject.toml`.

## Environment

### Linux sandbox

Use `pyproject.toml` as the installation entry point. For example, in an
isolated environment:

```console
python -m pip install -e ".[test]"
```

The build scripts use the compiler selected by setuptools. Linux outputs
normally include `libctd.so` and an ABI-tagged `_ctd_wrapper*.so` extension.

### Local Windows development

Start with the repository's Conda/Python and MSVC environment already
activated. The environment-management scripts under `pyenv/` are for the
user's existing Windows workflow; normal CTD builds and tests do not bootstrap
or modify that environment.

On MSVC, the standalone shared build produces `ctd.dll` and its `ctd.lib`
**import library** (plus associated intermediate output). The import library is
not a static copy of CTD: the dynamically linked `_ctd_wrapper*.pyd` dispatches
to `ctd.dll` at runtime. Artifact names differ on Linux and other platforms.

## CFFI API-mode design

Both wrapper builders use the same three CFFI operations:

1. `FFI.cdef()` receives declarations that become available through `ffi` and
   `lib`.
2. `FFI.set_source()` configures the generated extension's C source, headers,
   macros, compiler inputs, and linker inputs.
3. `FFI.compile()` generates and builds the native Python extension.

The source snippet passed to `set_source()` includes the real developer header:

```c
#include "ctd.h"
```

This is separate from CDEF parsing. `cdef()` parses only the declaration text
given to it; it does not preprocess `ctd.c` or follow C `#include` directives.

### Dual-use declaration header

`ctd_api.h` remains valid C source while also serving as the source for CDEF
input. `cdef_header.py` removes the include guard and the `CTD_API` or
`CTD_DATA_API` declaration prefix, which CFFI's CDEF parser cannot consume.
This avoids a manually maintained duplicate declaration file. `ctd.h` supplies
the C-facing macro definitions before including `ctd_api.h`.

### Test exposure of internal functions

Selected declarations and definitions use `CTD_API` rather than a literal
`static`. Production-style configuration can give those functions internal
linkage, while a dedicated test build can export them for the CFFI wrapper.
This keeps test access configurable instead of making private functions
permanently public.

## Building and running one mode

Run commands from the repository root.

For the dynamically linked wrapper, build the standalone library explicitly
before building the wrapper:

```console
python ctd/src/ctd/build_ctd.py
python ctd/src/ctd/build_ctd_wrapper.py
python ctd/src/ctd/ctd_demo.py
```

`build_ctd_wrapper.py` does not build its native prerequisite. Keeping the
standalone library build distinct makes compilation and linkage failures
visible at the correct stage.

The embedded wrapper needs no prebuilt CTD library:

```console
python ctd/src/ctd/build_ctd_wrapper_embedded.py
python ctd/src/ctd/ctd_demo.py
```

It compiles `ctd.c` into the extension; it does not link the extension to the
standalone CTD static library.

## Test matrix: separate processes, one wrapper name

The two builders intentionally produce the same module name. A native extension
cannot be reliably unloaded and replaced inside a running Python process, so
the mode comparison is a **sequential build-and-test matrix**, not a Pytest
parameter.

Run the complete matrix from the repository root in this order:

```console
# 1. Build the standalone CTD libraries.
python ctd/src/ctd/build_ctd.py

# 2. Build a wrapper dynamically linked to the shared CTD library.
python ctd/src/ctd/build_ctd_wrapper.py

# 3. Test that wrapper in a fresh Python process.
python -m pytest

# 4/5. Overwrite the stale generated wrapper outputs with an embedded build.
# If a platform/toolchain does not overwrite them, remove only
# ctd/src/ctd/_ctd_wrapper.c and ctd/src/ctd/_ctd_wrapper*.<extension suffix>,
# then rerun this command. Do not remove the standalone CTD library merely to
# switch wrapper modes.
python ctd/src/ctd/build_ctd_wrapper_embedded.py

# 6. Test the embedded wrapper in another fresh Python process.
python -m pytest
```

Each `python -m pytest` invocation imports exactly one already-built
`_ctd_wrapper`. The fixtures expose only that module's common `ffi` and `lib`
objects. Ordinary behavioral tests must remain build-mode agnostic: do not try
to unload `_ctd_wrapper`, swap native implementations during a test session, or
add a build-mode parameter while both wrappers share an import name. Tests of
the builder configuration itself may compare the builder modules without
loading two native implementations.

Generated `_ctd_wrapper.c`, native extensions, standalone libraries, object
files, and build directories are disposable build artifacts and should not be
committed.

## Introspection

A built wrapper exposes:

```python
from _ctd_wrapper import ffi, lib
```

`ffi` provides C types and C data construction/conversion operations. `lib`
provides the functions, constants, and globals declared through CDEF.
`ctd_introspect.py` records their top-level `ffi.CType` information in the
SQLite schema at `introspect/schema.sql`; nested CFFI types and fields can be
serialized as structured JSON. The added `name` and `category` columns identify
the C name and whether a record originated from the `ffi` or `lib` interface.

Run the diagnostic only after building either wrapper:

```console
python ctd/src/ctd/ctd_introspect.py
```

## Scope

This is an exploratory engineering repository, not a general C binding
generator. It deliberately does not attempt arbitrary preprocessing, libclang
source analysis, a replacement build system, or automatic normalization of
every nested CFFI object. The goal is a practical and inspectable CFFI/Pytest
workflow that keeps dynamic and embedded integration available for comparison.
