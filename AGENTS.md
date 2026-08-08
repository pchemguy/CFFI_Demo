## Project Orientation — Read This First

This repository is an experimental engineering project for developing **portable Pytest workflows that test deterministic C APIs through CFFI API mode**.

The demo C library is **CTD**. It exists primarily as a compact reference catalogue of Python/C boundary patterns rather than as production-library code. Keep CTD implementations small, deterministic, and easy to trace from declaration to implementation to test.

The project compares two CFFI integration modes:

1. **Dynamic wrapper** — build CTD as a standalone shared library, then link `_ctd_wrapper` against it.
2. **Embedded wrapper** — compile `ctd.c` directly into `_ctd_wrapper`; CTD symbols remain exported in this diagnostic build so native exports can be inspected.

Both modes expose the same Python import interface:

```python
from _ctd_wrapper import ffi, lib
```

CTD also supports separate linkage roles:

* normal production-style fallback: CTD functions/data have internal `static` linkage;
* standalone static library: ordinary external linkage;
* shared-library producer: exported external linkage;
* shared-library consumer: imported external linkage where required by the platform.

### Environment

First determine where you are running.

**Local Windows agent**

* Windows with `cmd.exe`.
* Conda-managed Python and MSVC are already activated before the agent starts.
* Do not bootstrap, activate, repair, replace, or otherwise modify that environment.
* Do not execute, edit, generate, delete, or rename anything under `/pyenv`.
* Do not require PowerShell, Bash, MSYS2, WSL, or another compatibility layer unless the task explicitly concerns one.
* Preserve the Python/setuptools-based portable native build scripts; do not replace them with `.bat` or direct-MSVC build scripts.

**Cloud Linux agent**

* Use root `pyproject.toml` as the authoritative Python environment/install entry point.
* Install project dependencies in the sandbox as needed.
* Use the C compiler/linker selected or discovered by setuptools.
* Do not emulate Windows artifact names or alter portable code merely to reproduce `.dll`, `.lib`, `.exp`, or `.pyd` outputs.

### Key Project Files

```text
ctd/src/ctd/
    ctd_api.h                     dual-use C/CDEF declarations
    ctd.h                         C header and linkage policy
    ctd.c                         deterministic CTD implementation
    cdef_header.py                narrow CDEF transformation
    build_ctd.py                  standalone native-library builder
    build_ctd_wrapper.py          dynamically linked CFFI builder
    build_ctd_wrapper_embedded.py embedded-source CFFI builder
    ctd_demo.py                   complete runtime demonstration
    ctd_introspect.py             reflection/database coordinator
    introspect/
        cffi_model.py
        database.py
        schema.sql

ctd/tests/
    conftest.py
    cffi_types.py
    test_cdef_header.py
    test_globals_status_and_scalars.py
    test_pointers_arrays_and_bytes.py
    test_strings_structures_and_ownership.py
    test_cffi_usage_patterns.py
```

Confirm the actual tree before editing; this list is orientation, not an exhaustive inventory.

### Architecture That Must Be Preserved

* `ctd_api.h` is the single declaration catalogue used by both C and CFFI.
* `ctd.h` supplies C-only includes, linkage macros, and then includes `ctd_api.h`.
* `cdef_header.py` mechanically transforms `ctd_api.h`; do not maintain a second handwritten CDEF declaration file.
* `FFI.cdef()` parses transformed declaration text. It does not preprocess arbitrary C, follow headers, or inspect `ctd.c`.
* `FFI.set_source()` includes the real `ctd.h`; the platform C compiler validates the actual declarations and layouts.
* Keep dynamic and embedded wrapper workflows independently usable.
* Generated wrapper/native artifacts are disposable and are never authoritative source.
* Pytest is the test runner. Tests should emphasize distinct CFFI boundary mechanics and API contracts, not merely one test per function.

### How This File Is Organized

The remaining sections provide detailed rules for:

1. [C declarations](## C Source and Declaration Architecture), [linkage](## CTD Linkage Model), and [style](## C Style).
2. [CFFI build and declaration handling](## CFFI API-Mode Build Architecture).
3. [supported boundary patterns](## Supported CFFI Boundary Patterns) and [ownership](## Ownership Rules).
4. [generated artifacts](## Generated and Build Artifacts), [introspection](## Introspection Model), and [tests](## Tests).
5. [Python/test style](## Python Style) and [validation](## Validation).
6. [coding-agent workflow](## Agent Workflow) and [change discipline](## Change Discipline).
7. [documentation rules](## Documentation Rules) and [non-goals](## Non-Goals Unless Explicitly Requested).

When a task is narrow, read this orientation first, then the applicable detailed section and the relevant source/tests before editing.

---

## C Source and Declaration Architecture

### `ctd.c`

`ctd.c` implements the fixture library. It intentionally exercises a practical range of CFFI interfaces:

* scalars and enums;
* writable and read-only globals;
* scalar pointers;
* typed arrays and byte buffers;
* NUL-terminated strings;
* structures, nested structures, fixed-size array fields, and tagged unions;
* borrowed and owned pointer returns;
* callbacks and returned function pointers;
* opaque handles and explicit release.

CTD is not intended to be production-database-grade defensive code. Do not add elaborate validation, abstraction, or edge-case machinery unless it serves a specific boundary pattern or contract being tested.

Keep individual examples deterministic and focused.

### `ctd.h` and `ctd_api.h`

The declaration architecture is intentionally split:

* `ctd.h` is the normal implementation/developer header.
* `ctd_api.h` contains declarations that are also transformed into CFFI CDEF input.

Do not merge these files merely to simplify the layout.

`ctd_api.h` must remain:

1. valid when included through `ctd.h` by a C compiler;
2. mechanically transformable into one coherent `FFI.cdef()` declaration stream.

When exposing a new API:

1. declare it in `ctd_api.h`;
2. implement it in `ctd.c`;
3. use the established linkage/data macros;
4. ensure `cdef_header.py` can transform the declaration without a manual duplicate;
5. add or update tests when the declaration introduces a meaningful new contract or CFFI usage pattern.

### CDEF Transformation

`cdef_header.py` performs a deliberately narrow textual transformation.

The current declaration catalogue is constrained so that C-only preprocessor wrapper lines can be stripped while preserving the declarations themselves. The transformer removes applicable lines beginning with directives such as:

```text
#if
#ifdef
#ifndef
#endif
#define
```

and removes API prefixes from declarations. `CTD_TEST_DATA_API` declarations become ordinary `extern` declarations for CDEF purposes.

This is **not a general C preprocessor**.

Do not introduce conditional declaration alternatives, `#else`/`#elif` branches, macro-generated declarations, or arbitrary preprocessing into `ctd_api.h` without first redesigning and testing the transformation contract.

Do not create a separately maintained CDEF header unless explicitly requested.

---

## CTD Linkage Model

Selected CTD declarations and definitions use configurable macros rather than literal storage-class/export syntax.

The conceptual modes are:

| Mode                      | Functions               | Data declarations                | Data definitions  |
| ------------------------- | ----------------------- | -------------------------------- | ----------------- |
| production/internal       | `static`                | `static`                         | `static`          |
| standalone static library | ordinary external       | `extern`                         | ordinary external |
| shared producer           | exported                | exported `extern`                | exported          |
| shared consumer           | imported where required | imported `extern` where required | not applicable    |

Typical macros include:

```text
CTD_TEST_API
CTD_TEST_DATA_API
CTD_TEST_DATA_DEF
```

On Windows shared-library builds these may expand to `__declspec(dllexport)` or `__declspec(dllimport)`. On GCC/Clang shared-library producers, default-visibility attributes may be used.

A static implementation library does **not** require DLL import/export or ELF visibility attributes; it requires ordinary external linkage.

Some `const` global declarations are omitted from internal/static declaration mode because an uninitialized file-scope `static const` declaration is not the desired definition pattern. Their initialized `CTD_TEST_DATA_DEF` definitions remain in `ctd.c`.

Preserve the distinction between declarations and definitions for global data.

Do not replace this scheme by permanently removing `static` from production-style symbols.

### Test-only interfaces

A directly tested C interface does **not** have to exist in production builds.

There are two valid patterns:

1. **Expose an existing production-internal interface for tests.** Keep the declaration and definition present in all builds and use the established test API macro so normal builds retain `static` linkage while test builds expose the symbol.
2. **Define a genuinely test-only interface.** When an API exists solely for testing or diagnostics, both its declaration in `ctd_api.h` and its matching definition in `ctd.c` may be enclosed in:

```c
#if defined(CTD_TEST)

/* declaration or definition */

#endif
```

Use the second pattern only when the interface itself should not exist in production; it is optional, not a requirement for every tested internal function.

Keep declaration and definition guards consistent. Any conditional wrapper added to `ctd_api.h` must also remain compatible with the deliberately narrow CDEF transformation used by `cdef_header.py`.

---

## C Style

Use One True Brace Style (1TBS): opening braces stay on the same line as function declarators and control statements, and else follows the preceding closing brace on the same line. All control blocks must include "{}" even when optional (for blocks containing a single statement).

Also:

* keep code valid for the project's declared C language level;
* prefer fixed-width types when the contract requires fixed width;
* preserve const-correctness;
* keep warning-clean builds under the active supported compiler;
* avoid unrelated formatting changes;
* do not introduce C++ constructs into C sources;
* document non-obvious pointer ownership, lifetime, size units, and release rules;
* avoid nondeterminism unless nondeterminism is itself the tested feature.

---

## CFFI API-Mode Build Architecture

The wrapper builders revolve around:

```python
ffibuilder.cdef(...)
ffibuilder.set_source(...)
ffibuilder.compile(...)
```

Their roles are distinct:

* `cdef()` defines the declarations represented through `ffi` and `lib`;
* `set_source()` defines the generated extension translation unit, real header include, sources, macros, include paths, libraries, and link settings;
* `compile()` generates and builds the native extension.

The generated C source must include the real developer header:

```c
#include "ctd.h"
```

Do not assume `cdef()` parses `ctd.c` or follows C preprocessor includes.

### Dynamic Wrapper

The normal sequence is:

1. run `build_ctd.py`;
2. run `build_ctd_wrapper.py`;
3. import/use `_ctd_wrapper`.

The wrapper is a consumer of the separately built shared CTD library.

On MSVC, distinguish carefully between:

* the standalone static CTD `.lib`;
* the `.lib` import library associated with `ctd.dll`.

They are different artifacts despite sharing the extension.

On Linux, use the platform-native static archive/shared-library/Python-extension conventions; do not require Windows by-products.

### Embedded Wrapper

`build_ctd_wrapper_embedded.py` compiles `ctd.c` directly into the generated Python extension.

It must not require a prebuilt CTD shared library or import library.

The embedded build intentionally exports CTD symbols from the resulting `.pyd`/`.so` for diagnostic inspection even though those exports are not needed for normal internal wrapper calls.

From Python, dynamic and embedded wrappers should expose equivalent CTD behavior unless a task explicitly studies a difference.

### Build-Script Responsibility

Keep native stages explicit.

Do not silently make the dynamic wrapper builder invoke the standalone CTD builder as an implicit prerequisite unless the task explicitly redesigns orchestration.

Preserve the setuptools/distutils compiler abstraction used by the portable build scripts rather than replacing it with hard-coded MSVC or GCC command scripts.

---

## Supported CFFI Boundary Patterns

Tests and demos are intended as few-shot reference material for coding agents. Prefer clear examples of distinct boundary mechanics over redundant API-name coverage.

Important represented patterns include:

* scalar arguments and returns;
* enum constants;
* writable and read-only globals;
* `ffi.new("T *")` for `OUT` and `INOUT` scalar storage;
* `ffi.new("T[]", ...)` for caller-owned C arrays;
* `ffi.NULL` and NULL/count contracts;
* explicit count/capacity/required-size protocols;
* `ffi.string()` for copying NUL-terminated C strings;
* `ffi.unpack()` for copying typed C arrays;
* `ffi.buffer()` for viewing C memory;
* `ffi.from_buffer()` for exposing Python-owned buffer storage directly to C;
* structures returned by value;
* pointer-to-structure calls;
* nested structure initialization from Python mappings;
* fixed-size array fields inside structures;
* tagged unions;
* borrowed pointers embedded in output structures;
* borrowed static returns;
* CTD-owned allocations with explicit C release;
* opaque handles with generic or type-specific destruction;
* synchronous `ffi.callback()` invocation;
* `ffi.new_handle()` / `ffi.from_handle()` for Python objects passed through `void *`;
* returned C function pointers.

Do not infer a pointer contract solely from its C spelling. For each pointer establish:

* direction: `IN`, `OUT`, or `INOUT`;
* shape;
* nullability;
* count/capacity and its unit;
* ownership;
* lifetime/retention;
* exact release function, if any;
* expected output state on failure.

Callbacks and Python-owned pointers in the supported runtime profile are synchronous and not retained after the call. Retained/asynchronous callback systems are outside scope unless explicitly requested.

---

## Ownership Rules

1. `ffi.new()` memory is Python/CFFI-owned. Keep the owning cdata alive while C or any alias uses it. Never pass it to a CTD deallocator.
2. `ffi.from_buffer()` exposes Python-owned memory; keep the underlying Python buffer alive and compatible with the requested access.
3. Borrowed C pointers are not freed by Python. Copy them when independent Python lifetime is required.
4. CTD-owned allocations are released exactly once with the documented release function.
5. Do not interchange Python/CFFI allocation and CTD allocation/deallocation.
6. If an output structure contains a pointer aliasing caller storage, keep the caller's owning cdata alive while that alias is used.
7. Keep callback and handle cdata alive for every C call that may use them.
8. Use `try/finally` or `yield` fixtures for owned C resources so cleanup occurs even when assertions fail.

---

## Tests

Pytest is the intended test runner.

Important files currently include:

```text
ctd/tests/conftest.py
ctd/tests/cffi_types.py
ctd/tests/test_cdef_header.py
ctd/tests/test_globals_status_and_scalars.py
ctd/tests/test_pointers_arrays_and_bytes.py
ctd/tests/test_strings_structures_and_ownership.py
ctd/tests/test_cffi_usage_patterns.py
```

The test suite has two simultaneous purposes:

1. verify CTD contracts;
2. serve as a compact few-shot catalogue of correct CFFI usage patterns.

When adding tests:

* trace the target declaration into `ctd.c` before deriving expectations;
* distinguish success, boundary, and meaningful failure cases;
* use descriptive parameter IDs;
* use sentinels where output-preservation behavior matters;
* explicitly model ownership and cleanup;
* avoid multiplying tests that demonstrate no new contract or CFFI mechanic.

Do not infer behavior from an existing test name and copy it blindly to another API.

---

## Generated and Build Artifacts

Generated outputs are disposable unless a task explicitly targets them.

Typical artifacts include:

```text
_ctd_wrapper.c
build/
Release/
*.obj
*.o
*.lib
*.a
*.exp
*.dll
*.so
*.pyd
cffi_model.db
```

Rules:

* do not hand-edit `_ctd_wrapper.c`;
* do not treat generated binaries or databases as authoritative source;
* do not commit build products unless repository policy explicitly requires them;
* remove only relevant stale generated artifacts when rebuilding;
* do not delete handwritten source or unrelated user data;
* treat platform-specific filenames as examples rather than portable requirements.

---

## Introspection Model

A built wrapper exposes:

```python
from _ctd_wrapper import ffi, lib
```

Conceptually:

* `ffi` supplies CFFI declaration/type information and cdata construction/conversion;
* `lib` exposes functions, constants, and global variables represented in the CDEF declaration model.

The introspection subsystem is:

```text
ctd_introspect.py
    -> introspect/cffi_model.py
    -> introspect/database.py
    -> introspect/schema.sql
```

`cffi_model.py` traverses top-level declarations and recursively records CFFI type properties such as:

* `cname`;
* `kind`;
* pointer/array item types;
* structure and union fields;
* function argument and result types;
* enum element mappings;
* recursive references.

Nested CFFI model objects may be serialized as deterministic structured values rather than normalized into a large relational schema.

`database.py` persists normalized records into SQLite.

Do not redesign the model casually. Schema changes must remain synchronized with extraction/persistence code and applicable diagnostics/tests.

Reflection here means reflection over declarations supplied to CFFI. It is not arbitrary reflection over `ctd.c`.

---

## Python Style

* Use modern annotations consistent with the supported Python version.
* Runtime-generated CFFI values may use the repository's explicit dynamic typing boundary (`CffiValue`).
* Prefer `pathlib.Path`.
* Keep build/compiler failures visible.
* Preserve deterministic ordering in generated diagnostic data.
* Separate transformations from filesystem/subprocess effects where practical.
* Prefer focused helper functions over growing a large unstructured `main()`.
* Avoid new dependencies where the standard library is sufficient.
* Do not perform network access during normal build/test operation.

---

## Validation

Run the narrowest relevant checks first, then broader validation when the change affects shared architecture.

For C declarations, linkage, implementation, or CFFI builder changes, normally validate both wrapper modes.

Typical sequence from the repository root:

```text
python ctd/src/ctd/build_ctd.py
python ctd/src/ctd/build_ctd_wrapper.py
python ctd/src/ctd/ctd_demo.py
(cd ctd && python -m pytest)
python ctd/src/ctd/ctd_introspect.py

python ctd/src/ctd/build_ctd_wrapper_embedded.py
python ctd/src/ctd/ctd_demo.py
(cd ctd && python -m pytest)
python ctd/src/ctd/ctd_introspect.py
```

Run consumers in fresh Python processes after replacing one `_ctd_wrapper` build with the other.

For Python-only introspection/database changes, run focused Python tests and the affected diagnostic path against a freshly built wrapper.

Discover actual project commands from `pyproject.toml`, `pytest.ini`, or current scripts rather than inventing a runner.

Never claim validation succeeded unless the command was actually executed successfully. If a platform/toolchain is unavailable, state exactly what was not validated.

---

## Change Discipline

Agents must:

1. inspect relevant source, declarations, builders, nearby tests, and applicable README material before editing;
2. identify handwritten source versus generated/build output;
3. make the smallest coherent change that satisfies the task;
4. preserve both dynamic and embedded workflows unless explicitly changing their architecture;
5. update declaration, definition, build configuration, tests, demo, introspection, and documentation together when a contract spans them;
6. preserve established filenames/interfaces unless a concrete need justifies a rename;
7. avoid introducing another build system for convenience;
8. preserve the local-Windows versus cloud-Linux environment model;
9. expose compiler, linker, import, and runtime failures rather than masking them with fallback behavior;
10. avoid speculative abstractions unsupported by an immediate project need;
11. preserve useful user-authored comments and experimental alternatives unless obsolete and removal is appropriate;
12. avoid unrelated formatting or stylistic rewrites.

---

## Agent Workflow

### 1. Establish Scope

Read:

* this file;
* relevant source/build files;
* nearby tests;
* the corresponding README section.

Identify which areas are affected:

```text
C declaration/implementation
standalone native build
dynamic wrapper
embedded wrapper
demo
tests
introspection/database
environment
```

### 2. Trace the Contract

For a C API change, trace:

```text
ctd_api.h
    -> CDEF transformation
    -> generated wrapper declaration model
    -> ctd.h / ctd.c
    -> build/link mode
    -> ffi/lib Python interface
    -> demo/tests/introspection
```

For native-build changes, distinguish compilation from linking and verify produced artifacts.

On Windows distinguish object files, static libraries, import libraries, DLLs, and `.pyd` extensions.

On Linux distinguish object files, static archives, shared libraries, and Python extension `.so` files.

### 3. Implement

Use targeted edits and preserve existing naming/architecture.

Add comments when they explain non-obvious CFFI, ABI, linkage, ownership, or platform-toolchain behavior; avoid comments that merely narrate obvious code.

### 4. Validate

Use the environment rules stated at the start of this file.

Fix the first meaningful failure at its cause rather than accumulating workarounds.

For linkage changes, successful compilation alone is insufficient: verify linking, import, and representative invocation as applicable.

### 5. Report

Summarize:

* source files changed;
* behavioral or architectural effect;
* commands executed;
* validation results;
* any platform or mode not validated.

Do not describe regenerated build artifacts as source modifications.

---

## Documentation Rules

Keep README and source documentation technically aligned with the current implementation.

In particular:

* distinguish CFFI API mode from ABI mode;
* distinguish an MSVC import library from a static implementation library;
* distinguish internal, plain-external, export, and import linkage;
* distinguish CDEF transformation from C preprocessing;
* distinguish CFFI declaration reflection from parsing arbitrary C source;
* distinguish borrowed, Python-owned, and CTD-owned memory;
* document dynamic and embedded wrapper modes separately;
* avoid claiming platform validation that was not actually performed;
* use current repository filenames and paths.

---

## Non-Goals Unless Explicitly Requested

Do not expand ordinary tasks into:

* a general-purpose C binding generator;
* libclang-based source parsing;
* a replacement native build system;
* support for arbitrary C preprocessor input;
* retained/asynchronous Python callbacks;
* arbitrary cyclic object-graph conversion;
* allocator interchange between C and Python;
* permanent export of all private C functions;
* replacement of CFFI by `ctypes`, SWIG, pybind11, or another bridge;
* normalization of every nested CFFI value into a complex relational database;
* unvalidated platform support.

The immediate objective is a **practical, controlled, portable CFFI/Pytest reference workflow for testing C code**.
