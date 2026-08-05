---
url: https://chatgpt.com/c/6a732fbb-6b04-83eb-99f4-3941570b5b0b
---
# AGENTS.md

## Purpose

This repository is an exploratory CFFI project for evaluating Python/Pytest workflows that test C code, including functions and variables that normally have internal linkage.

The demo C library is named **CTD**. The project compares two CFFI API-mode integration strategies:

1. Build CTD as a shared library and dynamically link the generated CFFI wrapper against it.
2. Compile `ctd.c` into the generated CFFI wrapper so the CTD implementation is embedded in the Python extension.

The project also investigates CFFI reflection and diagnostics for declarations supplied through `FFI.cdef()`.

This is an experimental engineering repository. Preserve its ability to compare alternative workflows rather than prematurely collapsing them into one implementation.

## Primary Platform

The primary and currently documented platform is:

- Windows
- `cmd.exe`
- Conda-managed Python
- MSVC toolchain

Do not assume Bash, GCC, Clang, Make, CMake, a system-wide Python installation, or POSIX filesystem semantics unless the task explicitly adds such support.

Use Windows-compatible paths and subprocess behavior. Do not introduce shell commands that require PowerShell or a Unix compatibility layer unless specifically requested.

## Environment Rules

The repository deliberately avoids relying on globally installed development tools.

The `/pyenv` directory contains scripts for bootstrapping and activating the local Python and MSVC environment:

- `Anaconda_bootstrap.yml`
- `Anaconda.yml`
- `Anaconda.bat`
- `msbuild.bat`
- `conda_far.bat`

Respect these constraints:

- Do not install packages globally.
- Do not modify the user's root environment.
- Do not assume `python`, `pip`, or MSVC are available before environment activation.
- Do not run `Anaconda.bat` when an existing project environment is already present.
- Treat `msbuild.bat` as a supporting activation script, not normally as the direct user entry point.
- Prefer running project commands from the activated shell created by `conda_far.bat`.
- Before changing environment scripts, inspect their current behavior and preserve their collision-avoidance checks.

## Repository Areas

The principal CTD sources are under:

```text
ctd/src/ctd/
```

Important files include:

```text
ctd_api.h
ctd.h
ctd.c
build_ctd.py
build_ctd_wrapper.py
build_ctd_wrapper_embedded.py
ctd_demo.py
ctd_introspect.py
introspect/cffi_model.py
introspect/database.py
introspect/schema.sql
```

Confirm the actual repository tree before editing. Do not infer that this list is exhaustive.

## C Source Architecture

### `ctd.c`

`ctd.c` implements the demo library. It contains small functions and data intended to exercise a broad range of CFFI-supported declarations, including:

- numeric scalars;
- strings;
- enumerations;
- structures;
- arrays;
- pointers;
- global variables;
- memory-management cases.

Keep examples small, deterministic, and focused on one interoperability behavior whenever practical.

### `ctd.h` and `ctd_api.h`

The public/declarative header is intentionally split:

- `ctd.h` is the normal C-facing header and includes `ctd_api.h`.
- `ctd_api.h` contains declarations intended to be transformed into `FFI.cdef()` input.

Do not merge these files merely to simplify the layout. The split is part of the experiment.

`ctd_api.h` is dual-use input. It must remain valid for the C compiler while also remaining mechanically transformable into CDEF text. CFFI CDEF input does not support general preprocessing, so build code removes only the unsupported wrapper material, principally:

- the include guard;
- the `CTD_API` declaration prefix.

When adding declarations intended for Python exposure:

1. Declare them in `ctd_api.h`.
2. Ensure they remain valid C declarations.
3. Ensure the existing CDEF transformation can process them without ad hoc manual copies.
4. Include implementation-facing definitions and macros in `ctd.h` or `ctd.c` as appropriate.

Do not create a manually maintained duplicate CDEF declaration file unless explicitly requested.

## Private-Function Test Exposure

The project explores testing functions that are `static` in production but exported in dedicated test builds.

Selected declarations and definitions use the configurable `CTD_API` macro instead of a literal `static` storage-class specifier. Build configuration determines whether `CTD_API` provides:

- internal linkage for production-style builds;
- export visibility for test builds;
- import visibility where required by a client build.

Preserve the production/test linkage distinction. Do not simply make private functions permanently public.

When adding a test-visible internal function, apply `CTD_API` consistently to its declaration and definition and verify both production-style and test-export build behavior.

## C Style

Use the repository's established C style.

The opening brace of a C function definition must be on the same line as the declarator:

```c
int ctd_example(int value){
    return value;
}
```

Do not use:

```c
int ctd_example(int value)
{
    return value;
}
```

Additional rules:

- Prefer explicit, portable C types where the example requires fixed width.
- Keep warning-clean MSVC builds.
- Avoid unrelated formatting changes.
- Do not introduce C++ constructs into C sources.
- Preserve const-correctness and pointer ownership semantics.
- Document ownership where a function returns or accepts allocated memory.
- Keep demo behavior deterministic unless nondeterminism is the feature being tested.

## CFFI Build Modes

### Dynamically Linked Wrapper

The dynamic sequence is:

1. Build CTD with `build_ctd.py`.
2. Build the CFFI wrapper with `build_ctd_wrapper.py`.
3. Run `ctd_demo.py` or applicable tests.

On Windows, the CTD build is expected to produce artifacts such as:

```text
ctd.dll
ctd.lib
ctd.exp
```

The `.lib` used by the wrapper is the MSVC import library for `ctd.dll`, not a copy of the DLL implementation.

The generated Python extension (`*.pyd`) links against the import library and dispatches calls to `ctd.dll` at runtime.

### Embedded Wrapper

`build_ctd_wrapper_embedded.py` builds the wrapper while compiling `ctd.c` into the Python extension.

This mode must not require a previously built CTD import library. It should retain behavior equivalent to the dynamic mode from the Python caller's perspective unless the experiment intentionally demonstrates a difference.

### Build-Script Responsibility

The wrapper build scripts are responsible for building CFFI wrappers only.

Do not silently make `build_ctd_wrapper.py` build the CTD DLL as an implicit prerequisite. Keep build stages explicit unless the task specifically redesigns orchestration.

## CFFI Configuration

The wrapper scripts revolve around:

```python
ffibuilder.cdef(...)
ffibuilder.set_source(...)
ffibuilder.compile(...)
```

Maintain the distinction between their roles:

- `cdef()` defines declarations visible through the generated `ffi` and `lib` interfaces.
- `set_source()` defines the generated extension module, inserted C source snippet, include paths, libraries, library directories, source files, and compiler/linker options.
- `compile()` generates and builds the native Python extension.

The source snippet passed to `set_source()` must include the actual C developer header, normally:

```c
#include "ctd.h"
```

Do not assume `cdef()` parses C implementation sources or follows C preprocessor includes. It parses the declaration text provided to it.

## Generated and Build Artifacts

Treat generated outputs as disposable unless a task explicitly targets generation output.

Typical generated artifacts include:

```text
_ctd_wrapper.c
_ctd_wrapper.cp###-win_amd64.pyd
Release/
build/
*.obj
*.lib
*.exp
*.dll
*.pyd
```

Rules:

- Do not hand-edit `_ctd_wrapper.c`; change the CFFI builder input instead.
- Do not commit generated binaries or intermediate build products unless repository policy explicitly requires them.
- Do not treat generated files as the authoritative source.
- Remove or rebuild stale artifacts when validating changes that affect declarations, compiler options, or linkage.
- Avoid deleting user data or unrelated build outputs.

## Introspection Model

A built wrapper exposes:

```python
from _ctd_wrapper import ffi, lib
```

Conceptually:

- `ffi` provides C type information and C data construction/conversion operations.
- `lib` exposes declared functions, constants, and global variables.

The introspection subsystem records top-level CFFI model information in SQLite:

- `ctd_introspect.py` coordinates inspection.
- `introspect/cffi_model.py` extracts and normalizes CFFI model data.
- `introspect/database.py` handles persistence.
- `introspect/schema.sql` defines the database schema.

The current design stores top-level `ffi.CType` information in a `ctypes` table. Nested `ffi.CType` and `_cffi_backend.CField` values may be represented as structured JSON rather than normalized into additional relational tables.

Two project-added fields identify each top-level record:

- `name`: the C identifier obtained from `ffi.list_types()` or a `lib` attribute;
- `category`: the originating interface, such as `ffi` or `lib`.

Do not redesign this model casually. Preserve deterministic serialization and stable inspection output. Any schema change must be accompanied by corresponding updates to extraction code and tests or diagnostics.

## Python Style

- Use modern Python type annotations consistent with the repository's supported Python version.
- Prefer `pathlib.Path` for filesystem paths, while preserving Windows behavior.
- Use `subprocess.run(..., check=True)` or explicit return-code handling for build commands.
- Keep build failures visible; do not suppress compiler or linker diagnostics.
- Separate pure transformation logic from filesystem and subprocess effects.
- Add focused functions rather than expanding `main()` into an unstructured procedure.
- Preserve deterministic output ordering.
- Avoid new dependencies when the standard library is sufficient.
- Do not perform network access during normal builds or tests unless the existing environment-bootstrap workflow explicitly requires it.

## Testing and Validation

Before declaring a change complete, run the narrowest relevant validation and then the broader available checks.

For C or CFFI declaration changes, normally validate both integration modes:

1. Clean stale wrapper and native build outputs as needed.
2. Build the standalone CTD library.
3. Build the dynamically linked wrapper.
4. Run the demo and relevant tests.
5. Build the embedded wrapper.
6. Run the same demo and relevant tests.
7. Run introspection if the change affects exposed types, functions, constants, or globals.

For Python-only introspection or database changes, run the relevant Python tests and execute the affected diagnostic path against a freshly built wrapper.

Do not claim a command passed unless it was actually executed successfully. When the active environment or toolchain is unavailable, report the exact validation that could not be performed.

Discover the repository's actual test command from `pyproject.toml`, test configuration, or existing scripts. Do not invent a test runner. Pytest is the intended Python test framework where tests exist.

## Change Discipline

Codex and other coding agents must follow these rules:

1. Inspect the relevant files before editing.
2. Identify whether a file is handwritten, generated, or a build artifact.
3. Make the smallest coherent change that satisfies the request.
4. Preserve the dynamic and embedded workflows unless explicitly changing both.
5. Update declarations, definitions, builders, demos, tests, and documentation together when the contract spans them.
6. Do not rename established files or interfaces without a concrete need.
7. Do not introduce a new build system merely for convenience.
8. Do not replace the project's explicit environment model with generic Python packaging assumptions.
9. Do not conceal unresolved compiler, linker, or runtime failures with fallback behavior.
10. Avoid speculative abstractions. This repository exists to evaluate concrete CFFI behavior.
11. Preserve user-authored comments and experimental alternatives unless they are demonstrably obsolete and removal is requested.
12. Never rewrite unrelated sections solely for style.

## Codex Workflow

For each task:

### 1. Establish Scope

Read:

- this file;
- the relevant source and build files;
- nearby tests;
- the corresponding README section.

State internally which workflow is affected:

- standalone CTD build;
- dynamic wrapper;
- embedded wrapper;
- demo;
- introspection/database;
- environment activation.

### 2. Trace the Contract

For a C API change, trace all applicable layers:

```text
ctd_api.h
    -> cdef transformation
    -> generated wrapper declaration
    -> ctd.h / ctd.c
    -> dynamic or embedded linker inputs
    -> ffi/lib Python interface
    -> demo/tests/introspection
```

For a build change, verify paths separately for MSVC compilation and linking. On Windows, distinguish:

- object files;
- static libraries;
- import libraries;
- DLLs;
- generated Python extension modules.

### 3. Implement

Use targeted edits. Preserve existing naming and architecture. Add comments only where they explain non-obvious CFFI, ABI, linkage, ownership, or Windows-toolchain behavior.

### 4. Validate

Execute relevant commands in the already activated project environment. Capture the first meaningful failure and fix its cause rather than layering workarounds.

For linkage changes, inspect both the build command and produced artifacts. Successful compilation alone is insufficient; import and function invocation must also work.

### 5. Report

Summarize:

- files changed;
- behavioral effect;
- commands executed;
- validation results;
- any unvalidated platform or mode.

Keep the report factual. Do not describe generated artifacts as source changes.

## Documentation Rules

The README is a working exploratory document. Preserve its technical terminology and architecture.

When updating documentation:

- distinguish CFFI ABI mode from API mode correctly;
- distinguish an MSVC import library from a static implementation library;
- distinguish CDEF parsing from C compiler preprocessing;
- distinguish CFFI's declaration model from reflection over arbitrary C source;
- describe dynamic and embedded builds separately;
- avoid claiming portability that has not been tested;
- use exact filenames and paths from the current repository.

## Non-Goals Unless Explicitly Requested

Do not expand the task into:

- a general-purpose C binding generator;
- libclang-based source parsing;
- a replacement build system;
- automatic support for arbitrary C preprocessor input;
- cross-platform support not validated by the project;
- normalization of every nested CFFI object into a complex relational schema;
- permanent export of all private C functions;
- replacement of CFFI with `ctypes`, SWIG, pybind11, or another bridge.

The immediate objective is to study and document a practical, controlled CFFI-based testing workflow.
