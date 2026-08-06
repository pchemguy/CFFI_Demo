# Direct C API testing with Pytest and CFFI

## Project objective

This repository demonstrates **direct Pytest testing of deterministic,
computational C APIs through CFFI API mode**.  The fixture library, **CTD**,
keeps each operation small enough that tests can concentrate on values crossing
the C/Python boundary, pointer contracts, failure atomicity, and ownership.

CTD also demonstrates deliberate **test-build exposure** of selected symbols
that have internal linkage in production-style builds.  Such declarations and
definitions use the configurable `CTD_API` macro: its normal fallback is
`static`, while dedicated standalone or embedded test builds give the wrapper
the visibility it needs.  The project does not make production-internal
functions permanently public.

This is CFFI **API mode**: CFFI generates and compiles a native extension using
declarations supplied to `FFI.cdef()` and a real C header supplied through
`FFI.set_source()`.  It is not CFFI ABI mode, in which Python loads a library at
runtime and calls it without compiling a C wrapper.

## Supported reusable interface profile

The reusable profile is defined by **how data moves and who owns it**, not just
by a catalogue of C spellings.  It covers deterministic, synchronous calls
whose input pointers are not retained after return, plus explicitly managed
opaque state.  A complete pointer profile records:

| Dimension | Values used here | Meaning |
| --- | --- | --- |
| **Direction** | `IN`, `OUT`, `INOUT`, returned `OUT` | Whether C reads, writes, mutates, or returns the data. |
| **Shape** | scalar, NUL-terminated string, typed array, byte buffer, structure, opaque handle | How the pointee is interpreted. |
| **Nullability** | non-NULL, nullable, or NULL only when count is zero / for a size query | The exact validity rule, not a general permission to pass NULL. |
| **Retention** | not retained, borrowed by a returned descriptor, or retained as handle state | Whether a pointer can outlive the call. |
| **Ownership** | Python/CFFI, borrowed library storage, or caller-owned CTD allocation | Which side controls lifetime and release. |
| **Size unit** | elements, bytes, bytes including NUL, or inferred by NUL | What a count or capacity actually measures. |

`const` supports the direction contract but does not by itself define lifetime
or ownership.  Similarly, `T *` alone does not say whether it is one scalar, an
array, nullable, borrowed, or owned; the complete profile must do so.

### Canonical catalogue

The catalogue below is the complete runtime profile implemented by CTD.  The
names link directly to declarations and tests rather than implying that every
C function with a superficially similar type is safe to use the same way.

1. **Globals, constants, and status values.** Read/write isolated test state
   (`ctd_global_counter`, `ctd_global_last_status`, `ctd_global_scale`), read
   exported constants, reset state, increment the counter, and turn statuses
   into borrowed static names with `ctd_status_name()`.  `ctd_version()` is also
   a borrowed static string.  Tests reset mutable globals around cases.
2. **Scalar/value calls.** Values flow entirely by value through `ctd_add()`,
   `ctd_negate_i32()`, `ctd_add_u64()`, and `ctd_hypot_squared()`.
   `ctd_divide()` adds a non-NULL, caller-owned `OUT SCALAR`; failure leaves it
   unchanged.
3. **Scalar pointers.** `ctd_get_magic()` writes one caller-owned scalar;
   `ctd_increment()` mutates one; `ctd_swap_i32()` mutates two.  All are
   non-NULL and not retained.
4. **Typed arrays.** `ctd_sum_i32()` reads an `IN ARRAY`; `ctd_reverse_i32()`
   and `ctd_scale_i32()` mutate `INOUT ARRAY` storage; and
   `ctd_compute_stats_i32()` writes an `OUT STRUCT`.  Counts are `int32_t`
   elements.  `ctd_make_sequence_i32()` is the canonical size-query / explicit
   capacity / caller-buffer operation.  `ctd_borrow_sequence_i32()` returns a
   read-only static array plus an element count.  `ctd_alloc_sequence_i32()`
   returns a CTD allocation released by `ctd_free()`.
5. **Byte buffers.** `ctd_copy_bytes()` separates source count, destination
   capacity, and required count, all measured in bytes; a NULL destination is
   permitted for its size query.  `ctd_xor_bytes()` mutates an explicit-length
   buffer, while `ctd_checksum_bytes()` reads one and writes a scalar result.
   Embedded zero bytes are ordinary data.
6. **Strings.** `ctd_utf8_byte_size()` consumes a nullable, borrowed-for-call
   NUL-terminated string and reports encoded bytes, not Unicode code points.
   `ctd_select_static_string()` returns borrowed static storage;
   `ctd_alloc_greeting()` returns CTD-owned storage released with `ctd_free()`;
   `ctd_ascii_upper()` mutates a caller string with an explicit capacity; and
   `ctd_copy_string()` supports a size query and a caller destination whose
   capacity and required size both include the terminating NUL.
7. **Structures and tagged values.** `ctd_point_make()` and `ctd_point_add()`
   return structures by value; `ctd_point_dot()` borrows two input structures
   for the call; and `ctd_point_translate()` mutates one.  The family also
   includes `ctd_record_initialize()`, the `ctd_value_from_i64()` and
   `ctd_value_from_f64()` tagged-union constructors and `ctd_value_as_f64()`,
   borrowed `ctd_default_config()` plus
   `ctd_range_apply()`, and descriptors from `ctd_describe_i32()` and
   `ctd_static_descriptor()`.  A dynamic descriptor's `values` aliases its
   input, so the owning input cdata must remain alive; a static descriptor and
   its nested fields are all borrowed and read-only.
8. **Opaque handles and exact release.** `ctd_counter_create()` returns simple
   CTD-owned state that is used by `ctd_counter_get()` / `ctd_counter_add()` and
   released with `ctd_free()`.  `ctd_accumulator_create()` returns a genuinely
   opaque object with nested resources; after `add` / `get`, it must be released
   with the type-specific `ctd_accumulator_destroy()`, never `ctd_free()`.
9. **Failure and capacity protocol across the families.** Status-returning
   calls preserve caller `OUT`/`INOUT` objects on failure unless explicitly
   documented otherwise.  Valid size queries still write the required size
   when returning `CTD_ERROR_CAPACITY`.  Tests use sentinels to prove that C did
   not partially modify other output.

The declaration comments in
[`ctd_api.h`](ctd/src/ctd/ctd_api.h) are authoritative for each parameter's
direction, shape, nullability, retention, owner, and size unit.

## Ownership rules (read before writing a test)

> 1. **Memory created by `ffi.new()` remains Python/CFFI-owned.** Keep its
>    owning cdata alive while C or an alias uses it; never pass it to a C
>    deallocator.
> 2. **Borrowed C returns are copied and not freed.** Use `ffi.string()`,
>    `ffi.unpack()`, or another explicit copy while the documented lifetime is
>    valid.
> 3. **Owned C returns are released exactly once with the exact C
>    deallocator.** Use `ctd_free()` only where documented; use
>    `ctd_accumulator_destroy()` for an accumulator.
> 4. **Caller buffers include explicit capacities.** Keep counts and their
>    units separate from allocated capacity; string capacities include NUL when
>    the contract says so.
> 5. **C and Python allocators are never mixed.** Python/CFFI reclaims
>    `ffi.new()` storage; CTD reclaims CTD allocations.

The same rules apply on success, assertion failure, and Python exceptions, so
owned objects belong in `try/finally` blocks or `yield` fixtures.

## Header architecture and CFFI API-mode compilation

There is one declaration source, not a handwritten CDEF duplicate:

```text
ctd_api.h
    -> cdef_header.load_cdef_header()
    -> FFI.cdef(transformed declarations)
    -> generated _ctd_wrapper extension

ctd.h -> #include "ctd_api.h"
    -> FFI.set_source(..., '#include "ctd.h"', ...)
    -> the platform C compiler
```

* `ctd_api.h` contains the dual-use typedefs, enums, globals, and function
  prototypes.  It is valid input when included by a C compiler and is the
  mechanically transformed declaration input for CFFI.
* `ctd.h` supplies the standard includes (`stddef.h`, `stdint.h`), visibility
  and linkage macros, C++ linkage guards, and then includes `ctd_api.h`.
* `cdef_header.py` removes **only** CDEF-unsupported wrapper material: the API
  header's include guard and the `CTD_API` / `CTD_DATA_API` declaration
  prefixes (the data prefix becomes `extern`).  It does not maintain a second
  set of declarations or generally preprocess the header.
* `FFI.cdef()` parses only the transformed declaration text.  It does **not**
  preprocess `#include` directives, follow `ctd.h`, or parse `ctd.c`.
* `FFI.set_source()` supplies a C snippet containing the real developer header,
  `#include "ctd.h"`, as well as sources, macros, include paths, and link
  settings.  The platform compiler, not the CDEF parser, processes that header.

This separation lets the compiler verify real declarations and layouts while
CFFI exposes the corresponding `ffi` and `lib` interfaces.

## Build modes and platform artifacts

Both modes deliberately generate the same import name, `_ctd_wrapper`, so the
same demo and tests exercise both.  A Python process must load only the wrapper
built for its current matrix step.

### Dynamically linked wrapper

`build_ctd.py` first builds CTD independently.  Then
`build_ctd_wrapper.py` builds only the CFFI extension and links it against the
standalone shared library; it does not silently build that prerequisite.

* **Windows/MSVC:** the shared build produces `ctd.dll`, with executable CTD
  code, and `ctd.lib`, the MSVC **import library** used at wrapper link time
  (plus normal linker/build by-products such as `.exp`).  This `ctd.lib` is not
  a static implementation library.  The platform-tagged `_ctd_wrapper*.pyd`
  loads and dispatches to `ctd.dll` at runtime.  The standalone builder also
  creates a separate static library under its build directory, but the dynamic
  wrapper does not use it.
* **Linux:** the standalone shared object is normally `libctd.so`, and CFFI
  builds a platform/ABI-tagged `_ctd_wrapper*.so` Python extension linked to
  it.  Windows `.dll`, `.lib`, `.exp`, and `.pyd` names are not portable
  requirements.

### Embedded wrapper

`build_ctd_wrapper_embedded.py` compiles `ctd.c` directly into the generated
Python extension.  It needs no previously built CTD shared or import library
and does not link a static CTD implementation library.  The result is a
platform-tagged `_ctd_wrapper*.pyd` on Windows or `_ctd_wrapper*.so` on Linux,
with the CTD implementation inside that extension.

## Environment setup

Commands below start at the **repository root** unless a command explicitly
changes directory.

### Local Windows agent (`cmd.exe`)

Use the Conda-managed Python and activated MSVC environment already present in
the process.  Do not bootstrap, activate, repair, or replace it; do not execute
or modify `pyenv/`.  Confirm that the existing environment provides the
dependencies from `pyproject.toml`, then use the same `python` executable for
the build, demo, and tests.

### Cloud Linux sandbox

Create or select an isolated environment as appropriate for the sandbox and
use root `pyproject.toml` as the authoritative installation entry point:

```console
python -m pip install -e ".[dev]"
```

The build scripts use the C compiler and linker selected by setuptools.  No
Windows toolchain or artifact emulation is required.

Before building a wrapper, collect the suite from the repository root and
inspect the complete node IDs.  Parameterized cases use explicit behavioral
IDs rather than value-derived IDs:

```console
python -m pytest --collect-only
```

Run the static checks from the repository root as well:

```console
python -m ruff check ctd/src/ctd/ctd_demo.py ctd/src/ctd/build_ctd.py ctd/src/ctd/build_ctd_wrapper.py ctd/src/ctd/build_ctd_wrapper_embedded.py ctd/src/ctd/cdef_header.py ctd/tests
python -m mypy ctd/src/ctd/ctd_demo.py ctd/src/ctd/build_ctd.py ctd/src/ctd/build_ctd_wrapper.py ctd/src/ctd/build_ctd_wrapper_embedded.py ctd/src/ctd/cdef_header.py ctd/tests
```

## Exact commands and sequential validation matrix

### Dynamic wrapper

From the repository root:

```console
python ctd/src/ctd/build_ctd.py
python ctd/src/ctd/build_ctd_wrapper.py
python ctd/src/ctd/ctd_demo.py
(cd ctd && python -m pytest)
python ctd/src/ctd/ctd_introspect.py
```

The subshell matters for tests: `ctd/pytest.ini` defines the actual test path
and adds `ctd/src` to Python's import path.  Introspection writes
`cffi_model.db` in the command's current directory, so the command above writes
it at the repository root.

### Embedded wrapper

The embedded builder overwrites the common wrapper module.  Run it and all
consumers in fresh processes:

```console
python ctd/src/ctd/build_ctd_wrapper_embedded.py
python ctd/src/ctd/ctd_demo.py
(cd ctd && python -m pytest)
python ctd/src/ctd/ctd_introspect.py
```

### Required comparison order

| Step | Mode | Command | What it validates |
| ---: | --- | --- | --- |
| 1 | standalone | `python ctd/src/ctd/build_ctd.py` | Native compilation, standalone static archive, shared library, and (on MSVC) DLL import library. |
| 2 | dynamic | `python ctd/src/ctd/build_ctd_wrapper.py` | Wrapper compilation and linkage against the shared CTD build. |
| 3 | dynamic | `python ctd/src/ctd/ctd_demo.py` | Import plus representative calls and ownership paths. |
| 4 | dynamic | `(cd ctd && python -m pytest)` | Full behavioral and CDEF suite in a fresh process. |
| 5 | dynamic | `python ctd/src/ctd/ctd_introspect.py` | Reflection/persistence against the dynamic wrapper. |
| 6 | embedded | `python ctd/src/ctd/build_ctd_wrapper_embedded.py` | Wrapper compilation with `ctd.c` embedded. |
| 7 | embedded | `python ctd/src/ctd/ctd_demo.py` | Import and the same behavior without a shared-library dependency. |
| 8 | embedded | `(cd ctd && python -m pytest)` | The same full suite in another fresh process. |
| 9 | embedded | `python ctd/src/ctd/ctd_introspect.py` | Reflection/persistence against the embedded wrapper. |

A native extension cannot be reliably unloaded and replaced in one Python
process; wrapper mode is therefore a sequential build concern, not a Pytest
parameter.  If a toolchain fails to overwrite a stale wrapper, remove only the
generated `_ctd_wrapper.c`, matching native extension, and wrapper build
directory before rebuilding—do not delete handwritten sources or conflate the
two build designs.

## Practical Pytest patterns

These excerpts are copied from the suite rather than maintained as separate
examples.  Pytest supplies the `ffi` and `lib` fixtures defined in
[`conftest.py`](ctd/tests/conftest.py), and each test module imports `pytest`
itself.  Follow the links beside each excerpt for the complete boundary and
failure cases.

### Status lookup and readable parameter IDs

From
[`test_globals_status_and_scalars.py`](ctd/tests/test_globals_status_and_scalars.py):

```python
@pytest.mark.parametrize(
    ("constant", "expected"),
    [
        pytest.param("CTD_OK", b"CTD_OK", id="ok"),
        pytest.param("CTD_ERROR_NULL", b"CTD_ERROR_NULL", id="null"),
        pytest.param("CTD_ERROR_RANGE", b"CTD_ERROR_RANGE", id="range"),
        pytest.param("CTD_ERROR_CAPACITY", b"CTD_ERROR_CAPACITY", id="capacity"),
        pytest.param("CTD_ERROR_ALLOCATION", b"CTD_ERROR_ALLOCATION", id="allocation"),
        pytest.param(
            "CTD_ERROR_DIVIDE_BY_ZERO",
            b"CTD_ERROR_DIVIDE_BY_ZERO",
            id="divide-by-zero",
        ),
        pytest.param(None, b"CTD_ERROR_UNKNOWN", id="unknown"),
    ],
)
def test_status_names(ffi, lib, constant: str | None, expected: bytes) -> None:
    status = 999 if constant is None else getattr(lib, constant)
    assert ffi.string(lib.ctd_status_name(status)) == expected
```

### Capacity query, exact capacity, and preserved sentinel

From
[`test_pointers_arrays_and_bytes.py`](ctd/tests/test_pointers_arrays_and_bytes.py).
Here `capacity`, `count`, and `required[0]` are counts of `int32_t` elements,
not byte counts:

```python
@pytest.mark.parametrize(
    ("capacity", "size_query", "expected_status", "storage_written"),
    [
        pytest.param(0, True, "CTD_ERROR_CAPACITY", False, id="size-query"),
        pytest.param(3, False, "CTD_ERROR_CAPACITY", False, id="one-short"),
        pytest.param(4, False, "CTD_OK", True, id="exact-capacity"),
        pytest.param(5, False, "CTD_OK", True, id="extra-capacity"),
    ],
)
def test_sequence_capacity_contract(
    ffi,
    lib,
    capacity: int,
    size_query: bool,
    expected_status: str,
    storage_written: bool,
) -> None:
    sentinel = [777] * 5
    buffer = ffi.NULL if size_query else ffi.new("int32_t[]", sentinel)
    required = ffi.new("size_t *", 999)
    status = lib.ctd_make_sequence_i32(10, 4, buffer, capacity, required)
    assert status == getattr(lib, expected_status)
    assert required[0] == 4
    if not size_query:
        expected = [10, 11, 12, 13, 777] if storage_written else sentinel
        assert list(buffer) == expected
        assert (list(buffer) != sentinel) is storage_written
```

The floating-point test in
[`test_globals_status_and_scalars.py`](ctd/tests/test_globals_status_and_scalars.py)
uses `pytest.approx()`.  The handle failure test in
[`test_strings_structures_and_ownership.py`](ctd/tests/test_strings_structures_and_ownership.py)
seeds an `int` output sentinel and proves that it is preserved:

```python
@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [(3.0, 4.0, 25.0), (-3.0, 4.0, 25.0), (0.0, 0.0, 0.0)],
    ids=["positive", "negative", "zero"],
)
def test_hypot_squared(lib, x: float, y: float, expected: float) -> None:
    assert lib.ctd_hypot_squared(x, y) == pytest.approx(expected)


def test_null_handle_failure_preserves_output(ffi, lib) -> None:
    result = ffi.new("int *", -999)
    assert lib.ctd_counter_get(ffi.NULL, result) == lib.CTD_ERROR_NULL
    assert result[0] == -999
```

### Borrowed copies and exact owned release

From
[`test_strings_structures_and_ownership.py`](ctd/tests/test_strings_structures_and_ownership.py):

```python
def unpack_i32(ffi, pointer, count: int) -> list[int]:
    return list(ffi.unpack(pointer, count))


def test_borrowed_sequence_is_copied_to_python_storage(ffi, lib) -> None:
    count = ffi.new("size_t *")
    borrowed = lib.ctd_borrow_sequence_i32(count)

    assert borrowed != ffi.NULL
    copied = unpack_i32(ffi, borrowed, count[0])
    assert copied == [2, 3, 5, 7, 11]
```

The copied Python list has no CTD lifetime requirement, and the borrowed
pointer is deliberately not freed.  In contrast, this owned greeting example
from the same test module releases the pointer even when an assertion or Python
exception interrupts the test:

```python
def copy_nullable_string(ffi, pointer) -> bytes | None:
    return None if pointer == ffi.NULL else ffi.string(pointer)


def test_owned_greeting_uses_explicit_try_finally(ffi, lib) -> None:
    greeting = lib.ctd_alloc_greeting(b"Pytest")
    assert greeting != ffi.NULL
    try:
        assert copy_nullable_string(ffi, greeting) == b"Hello, Pytest!"
    finally:
        lib.ctd_free(greeting)
```

An opaque accumulator requires its type-specific destructor rather than
`ctd_free()`.  The complete lifecycle is tested in
[`test_strings_structures_and_ownership.py`](ctd/tests/test_strings_structures_and_ownership.py):

```python
def test_accumulator_opaque_handle_lifecycle(ffi, lib) -> None:
    accumulator = lib.ctd_accumulator_create(2)
    assert accumulator != ffi.NULL
    try:
        assert lib.ctd_accumulator_add(accumulator, 20) == lib.CTD_OK
        assert lib.ctd_accumulator_add(accumulator, 22) == lib.CTD_OK
        result = ffi.new("int64_t *", -999)
        assert lib.ctd_accumulator_get(accumulator, result) == lib.CTD_OK
        assert result[0] == 42
    finally:
        lib.ctd_accumulator_destroy(accumulator)
```

## Advanced declaration and reflection examples

`ctd_api.h` intentionally includes declarations beyond the reusable few-shot
runtime profile:

* typedef chains and enums, including status, tagged-number, range-policy, and
  returned-operation kinds;
* the `ctd_number` union and `ctd_value` tagged structure;
* callback typedefs (`ctd_binary_callback`, `ctd_value_predicate`, and
  `ctd_message_callback`) and the returned `ctd_binary_operation` function
  pointer;
* incomplete/opaque types (`ctd_counter`, `ctd_accumulator`, and `ctd_graph`);
* the self-referential `ctd_node`, whose `next` and `child` members point to
  other nodes.

Their presence makes CFFI type reflection, nested field serialization, and
diagnostics representative.  It does **not** put Python callback invocation,
asynchronous pointer retention, arbitrary graph traversal, or general cyclic
object conversion inside the reusable few-shot profile.  The synchronous
`ctd_apply_callback()` and returned-operation demonstrations are focused
experiments: callback and user-data cdata must remain alive for the call, and
the borrowed function pointer must not be freed.

## Non-goals

This project is not:

* a general-purpose binding generator or libclang-based C parser;
* a claim that `cdef()` preprocesses arbitrary headers or reflects over
  `ctd.c`;
* a replacement build system or an attempt to hide native build/link errors;
* a framework for retained callbacks, asynchronous use of Python-owned
  pointers, arbitrary object graphs, or allocator interchange;
* an effort to permanently export every production-internal function;
* a replacement of CFFI with `ctypes`, SWIG, pybind11, or another bridge;
* a normalization of every nested CFFI object into a large relational schema;
* an attempt to collapse the dynamic and embedded workflows into one.

## Generated-artifact policy

Generated outputs are disposable and are not authoritative source.  Do not
hand-edit or commit `_ctd_wrapper.c`, wrapper `.pyd`/`.so` files, DLLs, shared
objects, `.lib`/`.a` archives, `.exp`, `.obj`/`.o` files, `build/`, `Release/`,
or generated `cffi_model.db` databases unless a task explicitly targets such an
artifact.  Change `ctd_api.h`, `ctd.h`, `ctd.c`, or the builder input instead,
then clean only stale generated outputs and rebuild.  Platform-specific names
describe observed outputs, not cross-platform requirements.

## Repository layout

```text
pyproject.toml                         project metadata and dependency groups
ctd/pytest.ini                        test discovery/configuration
ctd/tests/                            behavioral, ownership, and CDEF tests
ctd/src/ctd/
    ctd_api.h                         dual-use C/CDEF declarations
    ctd.h                             developer header and linkage policy
    ctd.c                             deterministic CTD implementation
    cdef_header.py                    narrow CDEF header transformation
    build_ctd.py                      standalone native library builder
    build_ctd_wrapper.py              dynamically linked CFFI builder
    build_ctd_wrapper_embedded.py     embedded-source CFFI builder
    ctd_demo.py                       complete runtime demonstration
    ctd_introspect.py                 reflection/database coordinator
    introspect/
        cffi_model.py                 CFFI model extraction/normalization
        database.py                   SQLite persistence
        schema.sql                    introspection schema
docs/                                 exploratory background notes
```

The `pigen/` experiment is separate from CTD.  The local Windows `pyenv/`
implementation is user environment-management infrastructure and is outside
normal project build and modification scope.

## Introspection workflow

After either wrapper has been freshly built, `_ctd_wrapper` exposes:

```python
from _ctd_wrapper import ffi, lib
```

`ffi` provides declared C type information and cdata construction/conversion;
`lib` exposes only globals, constants, and functions included in the CDEF
declaration model.  This is reflection over declarations given to CFFI, not
reflection over arbitrary implementation source.

Run `python ctd/src/ctd/ctd_introspect.py` from the repository root at the
corresponding dynamic and embedded matrix steps.  The coordinator obtains names
from `ffi.list_types()` and `lib`, records top-level `ffi.CType` descriptions,
adds `name` and `category` (`ffi` or `lib`), and inserts them into the
`ctypes` table defined by `introspect/schema.sql`.  Nested `ffi.CType` and CFFI
field values may be stored as deterministic structured JSON rather than being
expanded into more relational tables.  Remove a disposable prior
`cffi_model.db` when a clean diagnostic snapshot is required.

## Compact coding-agent prompt

The following prompt is intended for a coding agent when this repository is
mounted at `/cffi-ref` as a read-only reference:

> Use `/cffi-ref` as the reference implementation for designing testable C APIs
> and creating CFFI/Pytest tests. First inspect `/cffi-ref/AGENTS.md`,
> `/cffi-ref/README.md`, `/cffi-ref/ctd/src/ctd/ctd_api.h`,
> `/cffi-ref/ctd/src/ctd/ctd.h`, and `/cffi-ref/ctd/src/ctd/ctd.c`, then compare
> every relevant declaration and implementation with
> `/cffi-ref/ctd/tests/conftest.py` and the applicable
> `/cffi-ref/ctd/tests/test_*.py` modules. Do not infer
> behavior from test names or copy examples without tracing the C contract.
>
> **Testability design:** preserve the split-header pattern: keep mechanically
> transformable, dual-use API declarations in `ctd_api.h`; keep C-only macros,
> definitions, and developer-facing includes in `ctd.h`; and keep behavior in
> `ctd.c`. For production-internal functions that require direct test access,
> apply a configurable `CTD_API`-like macro consistently to both declaration and
> definition so production builds retain internal linkage while dedicated test
> builds export the symbol. Do not permanently make private functions public,
> duplicate CDEF declarations by hand, or confuse `cdef()` parsing with C
> preprocessing. Preserve and validate both the dynamically linked and
> embedded-source wrapper modes.
>
> **Test creation:** derive tests from the actual C contract and cover success,
> boundary, and failure behavior with descriptive explicit parameter IDs.
> Assert status codes, values, side effects, and failure atomicity; initialize
> outputs with sentinels and prove that documented failures do not partially
> modify them. Use fixtures with deterministic teardown for mutable globals and
> owned opaque handles. Run `python -m pytest --collect-only` and inspect node
> IDs, diagnose with focused modules, then run the full configured suite against
> freshly built dynamic and embedded wrappers in separate Python processes.
>
> CTD's reference patterns include fixed-width signed and unsigned scalars;
> enums and status returns; globals and constants; nullable `IN`, `OUT`, and
> `INOUT` pointers; counted arrays; byte buffers; NUL-terminated strings;
> caller-capacity/size-query APIs; structures, fixed arrays, tagged unions, and
> recursive declarations; borrowed storage; caller-released allocations;
> opaque handles; callbacks with user data; and returned function pointers.
> Give special attention to NULL/count combinations, element-versus-byte units,
> NUL capacity, integer limits and overflow, pointer retention and callback
> lifetime, borrowed-versus-owned data, matching allocator/free functions,
> teardown after assertion failures, global isolation, invalid discriminants,
> and unchanged outputs on error. Keep examples small and deterministic, and
> document any target-library contract that differs from CTD rather than
> silently imposing CTD behavior.
