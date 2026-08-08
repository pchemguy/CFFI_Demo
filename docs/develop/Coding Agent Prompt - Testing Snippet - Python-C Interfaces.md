---
url: https://chatgpt.com/c/6a74ac69-a4b0-83eb-915e-b82fd9a112d7
---

## Coding Agent Prompt - Testing Snippet - Python-C Interfaces

The following prompt is intended for a coding agent when this repository is mounted at "/cffi-ref/" as a read-only reference:

````markdown
## Testing Across Python–C Interfaces

Use the demo CTD library in "/cffi-ref/" as the reference implementation for designing testable C interfaces and creating CFFI/Pytest tests for other C projects.

Before designing tests, inspect the relevant files under "/cffi-ref":

* `AGENTS.md`
* `README.md`
* `ctd/src/ctd/ctd_api.h`
* `ctd/src/ctd/ctd.h`
* `ctd/src/ctd/ctd.c`
* `ctd/tests/conftest.py`
* applicable `ctd/tests/test_*.py` modules

---

### Function, Macro, and Globals Naming

Prefer library-specific prefixes to namespace all globals and functions regardless of production visibility, as tested library may be amalgamated into other projects.

For a library named "ctd", test builds may be conrolled by macros:

```text
CTD_TEST <- enables test builds
CTD_TEST_API
CTD_TEST_DATA_API
CTD_TEST_DEF_API
```

### Testability of Internal C Interfaces

Where direct testing requires access to identifiers that are private in production builds, apply configurable API macros consistently to declarations and definitions. For a library named "ctd", declarations may take forms such as:

```c
CTD_TEST_DATA_API int ctd_counter;
CTD_TEST_API const char *ctd_version(void);
```

Define the corresponding API/data macros in the library's C-only header so ordinary production builds may retain internal linkage while dedicated test builds can provide plain external linkage or shared-library export/import linkage as required.

---

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

---

### Annotating C API Contracts

When implementing or modifying C APIs that will be tested through Python/CFFI, make the boundary contract visible in the C declaration comments. Follow the compact style used in "/cffi-ref/ctd/src/ctd/ctd_api.h".

Do not restate ordinary C semantics mechanically. Use these defaults unless the declaration says otherwise:

* scalar parameters and by-value structures are ordinary value inputs;
* input pointers are not retained after the call;
* caller-provided `OUT` and `INOUT` storage remains caller-owned;
* borrowed library pointers must not be freed by the caller;
* status-returning functions leave caller-provided `OUT` and `INOUT` storage unchanged on failure;
* counts for typed arrays are measured in elements;
* counts and capacities for byte buffers are measured in bytes;
* NUL-terminated string size is inferred from the terminator;
* callbacks are synchronous and not retained unless explicitly documented.

Annotate the declaration when a pointer, return value, size parameter, lifetime rule, ownership rule, or failure behavior is not fully determined by those defaults.

For pointer parameters, use compact contract terms as applicable:

```text
DIRECTION:   IN | OUT | INOUT
SHAPE:       SCALAR | ARRAY | BUFFER | STRING | STRUCT | CALLBACK | OPAQUE
NULLABILITY: non-NULL | nullable | NULL only when count is zero | NULL for size query
RETENTION:   not retained | borrowed/retained beyond return
OWNERSHIP:   caller-owned | borrowed library-owned | CTD/target-owned
UNIT:        elements | bytes | bytes including NUL | inferred by NUL
```

Prefer declaration comments such as:

```c
/* result: OUT SCALAR; non-NULL. */
ctd_status ctd_get_magic(int32_t *result);

/* values: IN ARRAY; NULL only when count is zero; count unit: int32_t elements. */
ctd_status ctd_sum_i32(
    const int32_t *values,
    size_t count,
    int64_t *result
);

/*
** destination: OUT BUFFER; NULL for size query; capacity unit: bytes.
** required_count: OUT SCALAR; value unit: bytes.
*/
ctd_status ctd_copy_bytes(
    const uint8_t *source,
    size_t source_count,
    uint8_t *destination,
    size_t destination_capacity,
    size_t *required_count
);

/* RETURN: borrowed library-owned STRING; nullable; static lifetime. */
const char *ctd_select_static_string(int selector);

/* RETURN: caller-owned STRING; NULL on failure; release with ctd_free(). */
char *ctd_alloc_greeting(const char *name);
```

Do not repeat default properties such as "not retained" or "caller-owned" on every parameter when they add no information. State them only when needed to disambiguate the API or when the function departs from the defaults.

Always document these non-default cases explicitly:

* a pointer retained after the call;
* a returned pointer whose ownership or lifetime is not obvious;
* a returned allocation and its exact release function;
* an output structure containing borrowed pointer fields;
* a count or capacity whose unit is not the family default;
* NULL used as a size-query protocol;
* strings whose capacity includes the terminating NUL;
* a callback retained beyond the call;
* aliasing between input and output storage;
* output that may be modified on failure;
* required-size/count outputs that are intentionally written on `CTD_ERROR_CAPACITY` or another failure result.

Keep annotations adjacent to the declaration so that an agent implementing or testing the function has the contract in context. If implementation behavior and declaration comments disagree, resolve the discrepancy rather than inferring the contract from one side alone.

---

### Designing Tests Across the Python/C Boundary

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
* exact release function for every C-owned allocation.

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
Follow the target library's naming and build conventions rather than copying CTD macro and symbol names mechanically.
````
