# Direct C API Testing with Pytest and CFFI

## Project objective

This repository demonstrates **direct Pytest testing of deterministic, computational C APIs through CFFI API mode**. The fixture library, **CTD**, keeps each operation small enough that tests can concentrate on data crossing the C/Python boundary: values, pointers, arrays, buffers, structures, callbacks, failure behavior, lifetime, and ownership.

CTD also demonstrates deliberate **test-build exposure** of symbols that may have internal linkage in production builds. Functions and global data use configurable linkage macros:

* the normal production fallback gives CTD symbols internal `static` linkage;
* a standalone static-library build gives them ordinary external linkage;
* a shared-library producer exports them;
* a shared-library consumer imports them where the platform requires this;
* an embedded diagnostic wrapper may compile CTD directly into the Python extension while still exporting CTD symbols for inspection.

The project therefore does not require production-internal functions to remain permanently public merely to make them testable.

This project uses CFFI **API mode**. CFFI generates and compiles a native Python extension from declarations supplied to `FFI.cdef()` and a real C header included through `FFI.set_source()`. Depending on the build mode, the generated extension either links against the standalone CTD shared library or compiles `ctd.c` directly into the extension. In neither case does Python explicitly load the target library through CFFI ABI-mode `dlopen()` calls.

## Supported reusable interface profile

The reusable profile is defined by **how data moves and who owns it**, not merely by C declaration spelling. It covers deterministic synchronous calls, caller-owned storage, borrowed library storage, explicitly owned C allocations, synchronous callbacks, and explicitly managed opaque state.

A complete pointer profile records:

| Dimension       | Values used here                                                                                             | Meaning                                                                |
| --------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| **Direction**   | `IN`, `OUT`, `INOUT`, returned `OUT`                                                                         | Whether C reads, writes, mutates, or returns the data.                 |
| **Shape**       | scalar, NUL-terminated string, typed array, byte buffer, structure, callback/function pointer, opaque handle | How the pointee is interpreted.                                        |
| **Nullability** | non-NULL, nullable, NULL only when count is zero, or NULL for a size query                                   | The exact validity rule rather than a general permission to pass NULL. |
| **Retention**   | not retained, borrowed through another returned object, or valid as persistent handle state                  | Whether access can outlive the call and what keeps it valid.           |
| **Ownership**   | Python/CFFI, borrowed library storage, or caller-owned CTD allocation                                        | Which side controls lifetime and release.                              |
| **Size unit**   | elements, bytes, bytes including NUL, or inferred by NUL                                                     | What a count, length, capacity, or required size measures.             |

`const` supports the direction contract but does not by itself define ownership or lifetime. Likewise, `T *` alone does not say whether the pointer represents one scalar, an array, a string, nullable storage, borrowed storage, or an owned allocation. Those properties belong to the API contract.

### Canonical catalogue

CTD implements eight principal runtime families plus a cross-cutting failure/capacity protocol.

1. **Globals, constants, and status values.** Read/write isolated test state (`ctd_global_counter`, `ctd_global_last_status`, `ctd_global_scale`), read exported constants, reset state, increment the counter, and convert status values into borrowed static names with `ctd_status_name()`. `ctd_version()` is also a borrowed static string.

2. **Scalar and value operations.** Values flow entirely by value through `ctd_add()`, `ctd_negate_i32()`, `ctd_add_u64()`, and `ctd_hypot_squared()`. `ctd_divide()` adds a non-NULL caller-owned `OUT SCALAR`; failure leaves that output unchanged.

3. **Scalar pointers.** `ctd_get_magic()` writes one caller-owned scalar, `ctd_increment()` mutates one, and `ctd_swap_i32()` mutates two. These pointers are non-NULL and not retained.

4. **Typed arrays.** `ctd_sum_i32()` reads an `IN ARRAY`; `ctd_reverse_i32()` and `ctd_scale_i32()` mutate `INOUT ARRAY` storage; and `ctd_compute_stats_i32()` writes an `OUT STRUCT`. Counts are measured in `int32_t` elements. `ctd_make_sequence_i32()` demonstrates size query, explicit capacity, and caller-provided output storage. `ctd_borrow_sequence_i32()` returns a borrowed static array plus an element count, while `ctd_alloc_sequence_i32()` returns CTD-owned storage released by `ctd_free()`.

5. **Byte buffers.** `ctd_copy_bytes()` separates source count, destination capacity, and required count, all measured in bytes; a NULL destination is valid for the size-query path. `ctd_xor_bytes()` mutates explicit-length storage and is also used to demonstrate `ffi.from_buffer()` over mutable Python memory. `ctd_checksum_bytes()` reads an explicit-length buffer and writes an output scalar. Embedded zero bytes remain ordinary data.

6. **Strings.** `ctd_utf8_byte_size()` consumes a nullable NUL-terminated string and reports encoded byte length rather than Unicode code points. `ctd_select_static_string()` returns borrowed static storage; `ctd_alloc_greeting()` returns CTD-owned storage released with `ctd_free()`; `ctd_ascii_upper()` mutates caller-owned string storage under an explicit byte capacity; and `ctd_copy_string()` supports a required-size query and a caller destination whose capacity and required size include the terminating NUL.

7. **Structures, tagged values, and callback/function-pointer boundaries.** `ctd_point_make()` and `ctd_point_add()` return structures by value; `ctd_point_dot()` borrows two structures for the call; and `ctd_point_translate()` mutates one. `ctd_record_initialize()` demonstrates fixed-size character and numeric array fields inside a structure. The family also includes the `ctd_value` tagged union, nested `ctd_config` / `ctd_range` structures, borrowed configuration storage, and descriptors whose pointer fields may either alias caller-owned storage or refer to static library storage. `ctd_apply_callback()` demonstrates a synchronous Python callback and `void *` user data; `ctd_get_binary_operation()` demonstrates a borrowed callable function pointer returned from C.

8. **Opaque handles and exact release.** `ctd_counter_create()` returns simple CTD-owned state used through `ctd_counter_get()` and `ctd_counter_add()` and released with `ctd_free()`. `ctd_accumulator_create()` returns an opaque object containing nested allocated state; after `add` / `get`, it must be released with the type-specific `ctd_accumulator_destroy()`, never `ctd_free()`.

Across these families, **failure and capacity behavior is a separate contract dimension rather than another data shape**. Status-returning calls preserve caller-provided `OUT` or `INOUT` storage on failure unless explicitly documented otherwise. Valid size-query/capacity paths still report the required count or size when returning `CTD_ERROR_CAPACITY`. Tests use sentinels to verify that unrelated output storage was not partially modified.

The declaration comments in [`ctd_api.h`](ctd/src/ctd/ctd_api.h) are authoritative for each parameter's direction, shape, nullability, retention, ownership, and size unit.

## Ownership and lifetime rules

> 1. **Memory created by `ffi.new()` is Python/CFFI-owned.** Keep its owning cdata alive while C or a borrowed alias uses it. Never pass it to a CTD deallocator.
> 2. **Memory exposed with `ffi.from_buffer()` remains Python-owned.** The underlying Python buffer object must remain alive and suitably writable for the duration of C access.
> 3. **Borrowed C returns are not freed.** Copy them with `ffi.string()`, `ffi.unpack()`, or another explicit Python copy when independent lifetime is required.
> 4. **Owned C returns are released exactly once using their documented C release function.** Use `ctd_free()` only for allocations documented for that release path; use `ctd_accumulator_destroy()` for an accumulator.
> 5. **Pointers stored inside returned/output structures obey their own ownership contract.** For example, `ctd_describe_i32()` stores an alias to caller-owned input, so the owning input cdata must remain alive while that field is accessed.
> 6. **Callbacks and user-data objects must remain alive while C can use them.** The canonical synchronous callback example uses `ffi.callback()`, `ffi.new_handle()`, and `ffi.from_handle()`.
> 7. **Caller buffers have explicit capacities and units.** Keep logical counts separate from allocated capacity; string capacities include the terminating NUL where documented.
> 8. **C and Python allocators are never mixed.** Python/CFFI reclaims `ffi.new()` storage; CTD reclaims CTD allocations.

The same release rules apply when an assertion or Python exception interrupts a test, so owned C objects belong in `try/finally` blocks or `yield` fixtures.

## Header architecture and CFFI API-mode compilation

There is one declaration catalogue rather than a handwritten CDEF duplicate:

```text
ctd_api.h
    -> cdef_header.load_cdef_header()
    -> FFI.cdef(transformed declarations)
    -> generated _ctd_wrapper extension

ctd.h
    -> #include "ctd_api.h"
    -> FFI.set_source(..., '#include "ctd.h"', ...)
    -> platform C compiler
```

* `ctd_api.h` contains the dual-use typedefs, enums, globals, callback types, structures, and function prototypes.
* `ctd.h` supplies standard C includes, linkage/visibility macros, C++ linkage guards, and then includes `ctd_api.h`.
* `cdef_header.py` performs a deliberately narrow textual transformation for CFFI. It strips C preprocessor wrapper lines used by this declaration catalogue (`#if`, `#ifdef`, `#ifndef`, `#endif`, and `#define`) and removes API declaration prefixes; `CTD_DATA_API` becomes `extern` for CDEF purposes.
* This transformation is **not a general C preprocessor**. The API declaration file is intentionally constrained so that removing those wrapper lines leaves one coherent declaration stream.
* `FFI.cdef()` parses only that transformed declaration text. It does not follow `#include` directives, preprocess arbitrary C, or inspect `ctd.c`.
* `FFI.set_source()` supplies a real compiler translation unit containing `#include "ctd.h"` together with sources, macros, include directories, library directories, and link options. The platform C compiler therefore validates the actual C declarations and layouts.

This arrangement keeps C and CFFI declarations synchronized while still allowing the real C compiler to process platform-specific linkage details.

## Linkage modes

CTD separates symbol linkage from Python-level behavior.

### Production/internal mode

With no test API mode selected:

```c
CTD_API      -> static
CTD_DATA_API -> static
CTD_DATA_DEF -> static
```

This is the normal internal-linkage fallback.

### Standalone static-library mode

A static archive that will be linked from another translation unit requires ordinary external linkage:

```c
CTD_API      -> /* empty */
CTD_DATA_API -> extern
CTD_DATA_DEF -> /* empty */
```

No `dllexport`, `dllimport`, or ELF visibility attribute is required.

### Shared-library producer

On Windows/MSVC:

```c
CTD_API      -> __declspec(dllexport)
CTD_DATA_API -> extern __declspec(dllexport)
CTD_DATA_DEF -> __declspec(dllexport)
```

On GCC/Clang shared-library builds:

```c
CTD_API      -> __attribute__((visibility("default")))
CTD_DATA_API -> extern __attribute__((visibility("default")))
CTD_DATA_DEF -> __attribute__((visibility("default")))
```

### Shared-library consumer

On Windows/MSVC:

```c
CTD_API      -> __declspec(dllimport)
CTD_DATA_API -> extern __declspec(dllimport)
```

On ordinary ELF platforms, no import attribute is required; declarations use normal external linkage.

## Build modes and platform artifacts

Both wrapper build modes deliberately generate the same import name, `_ctd_wrapper`, so the same demo and test suite exercise either implementation. A Python process must load only the wrapper produced for its current matrix step.

### Standalone CTD build

`build_ctd.py` builds:

* a standalone static CTD library using plain external linkage;
* a standalone shared CTD library using exported symbols;
* on MSVC, the DLL import library required by clients of the shared build.

On Windows, this means the project can contain two different `.lib` artifacts with different purposes:

* a **static implementation library**, containing CTD object code;
* an **import library** for `ctd.dll`, containing linker metadata for the shared-library exports.

Their location distinguishes them; they are not interchangeable.

### Dynamically linked wrapper

`build_ctd_wrapper.py` builds the CFFI extension without compiling `ctd.c`. The generated wrapper is linked against the standalone CTD shared library.

On Windows/MSVC:

```text
_ctd_wrapper*.pyd
        |
        +-- linked through ctd.lib import library
        |
        +-- loads ctd.dll at runtime
```

On Linux:

```text
_ctd_wrapper*.so
        |
        +-- linked against libctd.so
```

The wrapper is therefore a **shared-library consumer**.

### Embedded wrapper

`build_ctd_wrapper_embedded.py` compiles `ctd.c` directly into the generated Python extension:

```text
_ctd_wrapper*.pyd / _ctd_wrapper*.so
        |
        +-- generated CFFI wrapper
        +-- CTD implementation
```

The embedded implementation does not need a standalone CTD library. CTD symbols are nevertheless exported from this diagnostic extension build so that the native export table can be inspected independently of whether those exports are required by CFFI internally.

In the builder this distinction is summarized by the `DYNAMIC` setting:

```python
# True: link the wrapper against the CTD shared library.
# False: embed CTD in the wrapper and export its symbols for diagnostic inspection.
DYNAMIC = True
```

## Environment setup

Commands below start at the **repository root** unless a command explicitly changes directory.

### Local Windows agent (`cmd.exe`)

Use the Conda-managed Python and already activated MSVC environment present in the process. Do not bootstrap, activate, repair, or replace it, and do not execute or modify `pyenv/`.

Confirm that the existing environment provides the dependencies declared in `pyproject.toml`, then use the same `python` executable for native builds, wrapper builds, the demo, introspection, and tests.

### Cloud Linux sandbox

Create or select an isolated environment appropriate for the sandbox and use root `pyproject.toml` as the authoritative Python installation entry point:

```console
python -m pip install -e ".[dev]"
```

The build scripts use the compiler and linker selected by setuptools. No Windows toolchain or Windows artifact emulation is required.

Before building a wrapper, collect the test suite from the repository root and inspect the complete node IDs:

```console
python -m pytest --collect-only
```

Parameterized cases use descriptive behavioral IDs rather than relying on automatically generated representations of values.

Run static checks from the repository root:

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

The subshell matters for tests because `ctd/pytest.ini` defines the test path and adds `ctd/src` to Python's import path.

Introspection writes `cffi_model.db` relative to the command's current working directory, so the command above writes it at the repository root.

### Embedded wrapper

The embedded builder replaces the common wrapper module. Run it and its consumers in fresh Python processes:

```console
python ctd/src/ctd/build_ctd_wrapper_embedded.py
python ctd/src/ctd/ctd_demo.py
(cd ctd && python -m pytest)
python ctd/src/ctd/ctd_introspect.py
```

### Required comparison order

| Step | Mode       | Command                                            | What it validates                                                                                  |
| ---: | ---------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
|    1 | standalone | `python ctd/src/ctd/build_ctd.py`                  | Native compilation, standalone static archive, shared library, and on MSVC the DLL import library. |
|    2 | dynamic    | `python ctd/src/ctd/build_ctd_wrapper.py`          | CFFI extension compilation and linkage against the standalone shared CTD build.                    |
|    3 | dynamic    | `python ctd/src/ctd/ctd_demo.py`                   | Import plus representative calls, ownership, callbacks, structures, and release paths.             |
|    4 | dynamic    | `(cd ctd && python -m pytest)`                     | Complete behavioral, CFFI-pattern, ownership, and CDEF suite in a fresh process.                   |
|    5 | dynamic    | `python ctd/src/ctd/ctd_introspect.py`             | CFFI declaration reflection and persistence against the dynamic wrapper.                           |
|    6 | embedded   | `python ctd/src/ctd/build_ctd_wrapper_embedded.py` | CFFI extension compilation with `ctd.c` embedded and CTD symbols exported diagnostically.          |
|    7 | embedded   | `python ctd/src/ctd/ctd_demo.py`                   | The same API behavior without a standalone shared-library dependency.                              |
|    8 | embedded   | `(cd ctd && python -m pytest)`                     | The same complete suite against the embedded implementation.                                       |
|    9 | embedded   | `python ctd/src/ctd/ctd_introspect.py`             | Reflection/persistence against the embedded wrapper.                                               |

A native extension cannot be reliably unloaded and replaced with another implementation in the same Python process. Wrapper mode is therefore a sequential build concern rather than a Pytest parameter.

If a toolchain cannot overwrite a stale wrapper, remove only generated `_ctd_wrapper.c`, the matching native extension, and wrapper build directories before rebuilding. Do not delete handwritten source files or conflate the two wrapper designs.

## Practical Pytest and CFFI patterns

The tests are intended not only to validate CTD but also to provide **few-shot examples of correct CFFI boundary usage**. They therefore favor tests that expose a distinct interface mechanic over redundant one-test-per-function coverage.

Pytest supplies `ffi` and `lib` fixtures from [`conftest.py`](ctd/tests/conftest.py). Runtime-generated CFFI objects cross the static typing boundary through the explicit `CffiValue = Any` alias in [`cffi_types.py`](ctd/tests/cffi_types.py).

### Status lookup and readable parameter IDs

From [`test_globals_status_and_scalars.py`](ctd/tests/test_globals_status_and_scalars.py):

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

From [`test_pointers_arrays_and_bytes.py`](ctd/tests/test_pointers_arrays_and_bytes.py). Here `capacity`, `count`, and `required[0]` are counts of `int32_t` elements rather than byte counts:

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

### Borrowed copies and exact owned release

From [`test_strings_structures_and_ownership.py`](ctd/tests/test_strings_structures_and_ownership.py):

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

The copied Python list has no CTD lifetime requirement and the borrowed pointer is not freed.

An owned C allocation uses explicit cleanup:

```python
def test_owned_greeting_uses_explicit_try_finally(ffi, lib) -> None:
    greeting = lib.ctd_alloc_greeting(b"Pytest")
    assert greeting != ffi.NULL

    try:
        assert ffi.string(greeting) == b"Hello, Pytest!"
    finally:
        lib.ctd_free(greeting)
```

An accumulator has a different release contract:

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

### Python buffer storage exposed directly to C

[`test_cffi_usage_patterns.py`](ctd/tests/test_cffi_usage_patterns.py) distinguishes separately allocated CFFI storage from direct borrowing of an existing Python buffer:

```python
def test_python_buffer_is_borrowed_without_ffi_allocation(ffi, lib) -> None:
    data = bytearray(b"abcd")
    buffer = ffi.from_buffer("uint8_t[]", data)

    status = lib.ctd_xor_bytes(buffer, len(data), 0x20)

    assert status == lib.CTD_OK
    assert data == bytearray(b"ABCD")
```

Here Python owns the `bytearray`; `ffi.from_buffer()` exposes that same storage to C rather than allocating and copying another array.

### Callback and Python object through `void *`

The synchronous callback example combines a declared callback typedef with CFFI handles:

```python
def test_callback_with_python_user_data(ffi, lib) -> None:
    context = {"weight": 10}
    user_data = ffi.new_handle(context)

    @ffi.callback("ctd_binary_callback")
    def weighted_add(left, right, opaque):
        callback_context = ffi.from_handle(opaque)
        return left + right * callback_context["weight"]

    result = ffi.new("int *", -999)

    status = lib.ctd_apply_callback(
        2,
        3,
        weighted_add,
        user_data,
        result,
    )

    assert status == lib.CTD_OK
    assert result[0] == 32
```

Both callback cdata and handle cdata remain alive for the C call. CTD does not retain either pointer after return.

### Returned C function pointer

A returned function pointer is borrowed executable library state and can be called directly while the library remains loaded:

```python
operation = lib.ctd_get_binary_operation(lib.CTD_BINARY_OPERATION_MULTIPLY)

assert operation != ffi.NULL
assert operation(6, 7) == 42
```

An unsupported operation kind returns `ffi.NULL`.

### Nested structures and fixed-size array fields

CFFI can initialize nested structures directly from Python mappings:

```python
config = ffi.new(
    "ctd_config *",
    {
        "range": {
            "minimum": -10.0,
            "maximum": 10.0,
        },
        "policy": lib.CTD_RANGE_CLAMP,
    },
)
```

Fixed-size arrays embedded in a structure remain directly accessible:

```python
record = ffi.new("ctd_record *")
assert lib.ctd_record_initialize(record, 77, b"sample") == lib.CTD_OK

assert record.id == 77
assert ffi.string(record.name) == b"sample"
assert list(record.values) == pytest.approx([1.0, 2.0, 3.0])
```

### Structure field aliasing caller-owned memory

`ctd_describe_i32()` intentionally places the input array pointer into an output descriptor. The owning CFFI array must therefore remain alive while the descriptor field is used:

```python
values = ffi.new("int32_t[]", [4, 8, 15, 16, 23, 42])
descriptor = ffi.new("ctd_descriptor *")

assert lib.ctd_describe_i32(values, 6, descriptor) == lib.CTD_OK
assert list(ffi.unpack(descriptor.values, descriptor.count)) == [
    4,
    8,
    15,
    16,
    23,
    42,
]
```

The descriptor does not become an independent owner of the array.

## Declaration and reflection examples

`ctd_api.h` intentionally includes declaration shapes beyond the minimum required to exercise every runtime branch:

* typedef chains and enums, including status, tagged-number, range-policy, and returned-operation kinds;
* the `ctd_number` union and `ctd_value` tagged structure;
* callback typedefs including `ctd_binary_callback`, `ctd_value_predicate`, and `ctd_message_callback`;
* the returned `ctd_binary_operation` function pointer;
* incomplete/opaque types including `ctd_counter`, `ctd_accumulator`, and `ctd_graph`;
* the self-referential `ctd_node`, whose `next` and `child` members point to other nodes.

Some of these declarations are primarily present to make CFFI type reflection and recursive field serialization representative. The runtime suite deliberately exercises only the callback/function-pointer cases that belong to the supported synchronous profile.

Retained callbacks, asynchronous use of Python-owned memory, and arbitrary cyclic graph conversion remain outside scope.

## Non-goals

This project is not:

* a general-purpose binding generator or general C parser;
* a claim that `cdef()` preprocesses arbitrary headers or reflects over `ctd.c`;
* a replacement native build system or an attempt to hide compiler/linker errors;
* a framework for retained callbacks or asynchronous use of Python-owned pointers;
* a general object-graph marshaller;
* a mechanism for allocator interchange between C and Python;
* an effort to permanently export every production-internal function;
* a replacement for CFFI with `ctypes`, SWIG, pybind11, or another bridge;
* an attempt to normalize every nested CFFI object into a large relational schema;
* an attempt to load dynamic and embedded wrappers simultaneously in one Python process.

## Generated-artifact policy

Generated outputs are disposable and are not authoritative source.

Do not hand-edit or commit generated `_ctd_wrapper.c`, wrapper `.pyd`/`.so` files, DLLs, shared objects, `.lib`/`.a` archives, `.exp`, `.obj`/`.o` files, build directories, or generated `cffi_model.db` databases unless a task explicitly targets one of those artifacts.

Change `ctd_api.h`, `ctd.h`, `ctd.c`, or the applicable builder input instead, then remove only stale generated outputs and rebuild.

Platform-specific artifact names describe observed outputs rather than cross-platform requirements.

## Repository layout

```text
pyproject.toml                         project metadata and dependency groups
ctd/pytest.ini                        test discovery/configuration
ctd/tests/
    cffi_types.py                     typing boundary for generated CFFI objects
    conftest.py                       ffi/lib and owned-resource fixtures
    test_cdef_header.py               declaration-transformation tests
    test_globals_status_and_scalars.py
    test_pointers_arrays_and_bytes.py
    test_strings_structures_and_ownership.py
    test_cffi_usage_patterns.py       focused CFFI boundary idioms
ctd/src/ctd/
    ctd_api.h                         dual-use C/CDEF declaration catalogue
    ctd.h                             C header and linkage policy
    ctd.c                             deterministic CTD implementation
    cdef_header.py                    narrow CDEF transformation
    build_ctd.py                      standalone native-library builder
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

The `pigen/` experiment is separate from CTD. The local Windows `pyenv/` implementation is user environment-management infrastructure and is outside normal project build and modification scope.

## Introspection workflow

After either wrapper has been freshly built, `_ctd_wrapper` exposes:

```python
from _ctd_wrapper import ffi, lib
```

`ffi` provides the CFFI declaration/type interface and cdata construction/conversion facilities. `lib` exposes globals, constants, and functions represented by the CDEF declaration model.

This is reflection over declarations supplied to CFFI, not reflection over arbitrary implementation source.

Run:

```console
python ctd/src/ctd/ctd_introspect.py
```

at the corresponding dynamic or embedded matrix step.

The coordinator obtains declared type names from `ffi.list_types()` and exported declaration names from `lib`. It recursively records CFFI `CType` properties such as `kind`, `cname`, pointer item types, function arguments/results, structure fields, enum mappings, and recursive references, then persists the normalized model to the `ctypes` table defined by `introspect/schema.sql`.

Nested CFFI type descriptions may be stored as structured JSON rather than expanded into a large relational model. Remove a disposable prior `cffi_model.db` when a clean diagnostic snapshot is required.

## Compact coding-agent prompt

The following prompt is intended for a coding agent when this repository is mounted at `/cffi-ref` as a read-only reference:

````markdown
## Testing Across Python–C Interfaces

Use the dummy `ctd` library in `/cffi-ref` as the reference implementation for designing testable C interfaces and creating CFFI/Pytest tests for other C projects.

### Testability of Internal C Interfaces

Where direct testing requires access to identifiers that are private in production builds, apply configurable API macros consistently to declarations and definitions.

For a library named `ctd`, declarations may take forms such as:

```c
CTD_DATA_API int ctd_counter;
CTD_API const char *ctd_version(void);
```

Define the corresponding API/data macros in the library's C-only header so ordinary production builds may retain internal linkage while dedicated test builds can provide plain external linkage or shared-library export/import linkage as required.

Follow the target library's naming and build conventions rather than copying CTD macro names mechanically.

### Designing Tests Across the Python/C Boundary

Before designing tests, inspect the relevant files under `/cffi-ref`:

* `AGENTS.md`
* `README.md`
* `ctd/src/ctd/ctd_api.h`
* `ctd/src/ctd/ctd.h`
* `ctd/src/ctd/ctd.c`
* `ctd/tests/conftest.py`
* the applicable `ctd/tests/test_*.py` modules

Trace each reference test to its C declaration and implementation. Do not infer behavior from test names or copy a CTD pattern without first establishing the target API contract.

For each target API, determine:

* parameter and return types;
* valid ranges and NULL rules;
* pointer direction (`IN`, `OUT`, or `INOUT`) and nullability;
* pointer shape: scalar, string, typed array, byte buffer, structure, callback, or opaque handle;
* string representation and encoding;
* count, length, capacity, and element-versus-byte units;
* ownership and lifetime of referenced or allocated memory;
* whether pointers or callbacks are retained beyond the call;
* mutations, side effects, and error reporting;
* guarantees about caller-provided output state after failure;
* the exact release function for every C-owned allocation.

Derive tests from that contract and cover meaningful success, boundary, and failure cases with descriptive parameter IDs.

Reuse the applicable CTD CFFI patterns for:

* scalar values and enums;
* readable/writable globals;
* `ffi.new()` scalar pointers and arrays;
* NULL and size-query paths;
* `ffi.string()` and `ffi.unpack()` borrowed copies;
* `ffi.buffer()` for views over C memory;
* `ffi.from_buffer()` for direct access to Python-owned buffers;
* structures by value and pointer-to-structure calls;
* fixed-size array fields and nested mapping initialization;
* tagged unions;
* borrowed pointer fields that alias caller-owned cdata;
* synchronous `ffi.callback()` calls;
* `ffi.new_handle()` / `ffi.from_handle()` user data;
* returned function pointers;
* CTD-owned allocations with explicit `try/finally` cleanup;
* opaque handles with type-specific destruction.

Use CTD as a pattern library, not as a substitute for analysis.
````
