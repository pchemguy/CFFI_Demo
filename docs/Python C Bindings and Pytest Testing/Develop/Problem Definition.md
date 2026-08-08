---
url: https://chatgpt.com/c/6a73901c-5730-83ed-a63c-4df0ff2d5d98
---

## 📗 Problem Definition

> [!NOTE] Prompt
> 
> I am thinking about reshuffling my CFFI demo code, which is right now just one big main def. BUT, I realize, what I actually need is to have a better definition of objective and scope. My ultimate objective is a robust means to test C code via Pytest. So the reason I have been thinking in terms of creating a higher-level auto wrapper is actually because I want test creation by a coding agent and I reasoned that pure Python interface might be simpler for an agent. But I also have to be practical and find a balance of my time invested in any contraptions, which proves to be substantial. So I may need to redefine the scope. I actually do not need to have agent to create tests for arbitrarily complex/obfuscated/twisted C code. So I guess I should better define a practical suite of patterns that would reasonably cover a large portion of non-system C use case (I do not care about hardware programming for now, or some special system things development; the focus is more on code where certain common algos and data handling is implemented for the sake of speed, no for the ability to entertain arbitrary control of the processes/environment). If I define such a suite of patterns, I can reshuffle the demo so that I would have basically a nice suite of one/few shot examples. I will accept the need to ask the agent to use CFFI directly, but I will be able supply the C source, function docstrings, if necessary, plus few shot examples.
>
> I am trying to define the patterns. I guess, supplying and receiving as return standard numeric scalars; supplying and returning strings (argument memory managed by cffi; for a return value, the string is immediately copied to memory managed by cffi, if it is not already implemented by cffi); supplying pointer to a structure/array with memory allocated by cffi; return structure pointer via return; and then, I guess, out and inout args).

### Objective and Scope

Your revised direction is sound: **do not build a general wrapper generator**. Define a constrained C interface profile that a coding agent can test directly through CFFI, supported by a compact catalogue of canonical examples.

The key is to define the scope in terms of **data-flow and ownership patterns**, not merely C types.

#### Proposed objective

Build a reusable Pytest/CFFI testing pattern for ordinary computational C modules that:

* implement algorithms or data transformations;
* expose deterministic, explicitly documented functions;
* do not depend heavily on operating-system state, hardware, signals, threads, callbacks, or opaque runtime environments;
* use a restricted set of explicit memory-management conventions;
* can be tested directly through CFFI without generated high-level Python wrappers.

The agent receives:

1. the C declarations;
2. the relevant implementation or documentation;
3. the ownership and parameter-direction contract;
4. a small set of representative CFFI/Pytest examples.

The agent then writes ordinary tests using `ffi` and `lib`.

---

#### The practical interface pattern set

I would divide the supported scope into the following groups.

##### 1. Scalar values

###### Scalar input

```c
int ctd_abs(int value);
double ctd_hypot(double x, double y);
```

Python:

```python
assert lib.ctd_abs(-7) == 7
assert lib.ctd_hypot(3.0, 4.0) == pytest.approx(5.0)
```

Cover:

* signed and unsigned integers;
* fixed-width integers;
* `size_t`, `ptrdiff_t`;
* `float`, `double`;
* `_Bool` or a documented integer Boolean convention;
* enums represented as integer values.

###### Scalar return

This is the simplest and most important pattern. It should include:

* exact integer results;
* approximate floating-point results;
* status-code returns;
* count or length returns.

###### Scalar out and inout

```c
ctd_status ctd_divide(
    double numerator,
    double denominator,
    double *result
);

void ctd_increment(int *value);
```

Python:

```python
result = ffi.new("double *")
status = lib.ctd_divide(8.0, 2.0, result)

assert status == lib.CTD_OK
assert result[0] == pytest.approx(4.0)
```

```python
value = ffi.new("int *", 7)
lib.ctd_increment(value)
assert value[0] == 8
```

These should be explicit patterns rather than treated as incidental pointer usage.

---

##### 2. Strings and byte sequences

Strings need a stricter contract than numeric scalars.

###### Input null-terminated text

```c
size_t ctd_utf8_length(const char *text);
```

Python:

```python
text = "Привет".encode("utf-8")
result = lib.ctd_utf8_length(text)
```

CFFI accepts Python `bytes` where a compatible `char *` or `const char *` argument is expected. The temporary C buffer remains valid for the duration of the call.

The contract must identify:

* whether the parameter is null-terminated;
* whether `NULL` is accepted;
* encoding: UTF-8, ASCII, arbitrary bytes, or another explicit encoding;
* whether embedded zero bytes are prohibited;
* whether the callee retains the pointer after returning.

For your scope, I recommend:

> Input string pointers are borrowed only for the duration of the call. The callee must not retain them.

###### Input byte sequence with explicit length

```c
uint32_t ctd_checksum(
    const unsigned char *data,
    size_t length
);
```

Python:

```python
data = b"\x00\x01\x02\xff"
result = lib.ctd_checksum(data, len(data))
```

This is distinct from a string. It permits embedded zero bytes and requires an explicit element count.

###### Returned borrowed string

```c
const char *ctd_status_name(ctd_status status);
```

Python:

```python
pointer = lib.ctd_status_name(lib.CTD_OK)
assert pointer != ffi.NULL
name = ffi.string(pointer).decode("utf-8")
```

A correction to your wording: `ffi.string(pointer)` copies C data into a **Python `bytes` object**, not into separately managed CFFI memory.

This pattern must specify that the pointer is:

* borrowed;
* valid for at least the duration of the copy;
* not to be freed by Python;
* null-terminated;
* encoded according to the documented encoding.

###### Returned owned string

```c
char *ctd_format_value(int value);
void ctd_free(void *pointer);
```

Python:

```python
pointer = lib.ctd_format_value(42)
assert pointer != ffi.NULL

try:
    value = ffi.string(pointer).decode("utf-8")
finally:
    lib.ctd_free(pointer)
```

This is worth supporting, but only with an explicit matching deallocator.

A strong rule would be:

> Python never directly frees C-owned memory. Every owned pointer returned by C must have a documented C deallocation function.

For safer tests:

```python
pointer = ffi.gc(lib.ctd_format_value(42), lib.ctd_free)
value = ffi.string(pointer).decode("utf-8")
```

However, explicit `try/finally` is often clearer in ownership tests.

###### Caller-provided output string buffer

```c
ctd_status ctd_format_value(
    int value,
    char *buffer,
    size_t capacity,
    size_t *required
);
```

This is a highly practical pattern because it avoids allocator crossing.

Python:

```python
capacity = 64
buffer = ffi.new("char[]", capacity)
required = ffi.new("size_t *")

status = lib.ctd_format_value(42, buffer, capacity, required)

assert status == lib.CTD_OK
assert ffi.string(buffer) == b"42"
assert required[0] == 3  ## Contract must say whether this includes NUL.
```

The capacity semantics must explicitly state whether capacity and required length are measured in:

* bytes;
* characters;
* typed elements;

and whether the terminating zero is included.

---

#####  3. Arrays

Arrays should be treated separately from strings even when represented by pointers.

######  Read-only input array

```c
double ctd_sum(
    const double *values,
    size_t count
);
```

Python:

```python
values = ffi.new("double[]", [1.0, 2.0, 3.0])
result = lib.ctd_sum(values, 3)

assert result == pytest.approx(6.0)
```

Contract:

* pointer refers to `count` readable elements;
* zero count semantics are documented;
* whether `NULL` is valid when count is zero;
* callee does not retain the pointer.

######  Mutable in-place array

```c
void ctd_scale(
    double *values,
    size_t count,
    double factor
);
```

Python:

```python
values = ffi.new("double[]", [1.0, 2.0, 3.0])
lib.ctd_scale(values, 3, 2.0)

assert list(values) == [2.0, 4.0, 6.0]
```

This is an array `inout` pattern.

######  Caller-provided output array

```c
ctd_status ctd_sequence(
    int start,
    int step,
    int *output,
    size_t capacity,
    size_t *written
);
```

This needs precise semantics for:

* capacity;
* number written;
* behavior on insufficient capacity;
* whether partial output is allowed;
* whether `written` means produced, required, or both depending on status.

######  Returned borrowed array

```c
const double *ctd_coefficients(size_t *count);
```

Python:

```python
count = ffi.new("size_t *")
pointer = lib.ctd_coefficients(count)

values = list(ffi.unpack(pointer, count[0]))
```

`ffi.unpack(pointer, count)` creates a Python representation of the pointed-to elements. This is the correct immediate-copy operation for a returned array.

The pointer must remain valid through the copy and must not be freed by Python.

######  Returned owned array

```c
double *ctd_make_sequence(
    size_t count
);

void ctd_free(void *pointer);
```

Python:

```python
pointer = lib.ctd_make_sequence(4)
assert pointer != ffi.NULL

try:
    values = list(ffi.unpack(pointer, 4))
finally:
    lib.ctd_free(pointer)
```

Again, the element count and deallocator are mandatory parts of the contract.

---

#####  4. Structures

You should distinguish four materially different structure patterns.

######  Structure passed by value

```c
typedef struct ctd_point {
    double x;
    double y;
} ctd_point;

double ctd_point_length(ctd_point point);
```

Python:

```python
point = ffi.new("ctd_point *", {"x": 3.0, "y": 4.0})
result = lib.ctd_point_length(point[0])
```

This is straightforward, but ABI-sensitive compared with pointer-based access. Because you are using CFFI API mode, it is reasonable to support.

######  Structure returned by value

```c
ctd_point ctd_point_make(double x, double y);
```

Python:

```python
point = lib.ctd_point_make(3.0, 4.0)

assert point.x == pytest.approx(3.0)
assert point.y == pytest.approx(4.0)
```

This is often preferable to returning an allocated structure pointer when the structure is small and plain.

######  Structure passed by pointer

```c
double ctd_point_length(const ctd_point *point);
```

Python:

```python
point = ffi.new("ctd_point *", {"x": 3.0, "y": 4.0})
result = lib.ctd_point_length(point)
```

This covers borrowed structure input.

######  Structure modified in place

```c
void ctd_point_translate(
    ctd_point *point,
    double dx,
    double dy
);
```

This is the structure `inout` pattern.

######  Caller-allocated output structure

```c
ctd_status ctd_point_parse(
    const char *text,
    ctd_point *result
);
```

Python:

```python
result = ffi.new("ctd_point *")
status = lib.ctd_point_parse(b"3.0,4.0", result)

assert status == lib.CTD_OK
assert result.x == pytest.approx(3.0)
assert result.y == pytest.approx(4.0)
```

For a pointer to a structure, CFFI allows both:

```python
result.x
result[0].x
```

######  Returned borrowed structure pointer

```c
const ctd_config *ctd_default_config(void);
```

The pointer is owned elsewhere. Python may inspect or copy its fields but must not free or mutate it.

A shallow Python copy can be made field by field. Copying arbitrary structures wholesale is not always sufficient because the structure may contain pointers.

######  Returned owned structure pointer

```c
ctd_context *ctd_context_create(void);
void ctd_context_destroy(ctd_context *context);
```

This is the opaque or owned-object lifecycle pattern:

```python
context = lib.ctd_context_create()
assert context != ffi.NULL

try:
    ...
finally:
    lib.ctd_context_destroy(context)
```

This pattern is valuable even when the structure definition is opaque:

```c
typedef struct ctd_context ctd_context;
```

It covers stateful algorithmic objects without requiring a high-level wrapper.

---

#####  5. Out and inout parameters

Rather than considering these a separate type category, define them as a **direction dimension** applicable to scalars, structures, and arrays.

Each pointer parameter should have one of:

* `IN`
* `OUT`
* `INOUT`

Additionally, pointer shape should be one of:

* `SCALAR`
* `STRUCT`
* `ARRAY`
* `BUFFER`
* `STRING`
* `OPAQUE`

These two dimensions already describe most practical cases.

For example:

| Declaration            | Direction | Shape  |
| ---------------------- | --------- | ------ |
| `const int *value`     | IN        | SCALAR |
| `int *result`          | OUT       | SCALAR |
| `ctd_point *point`     | INOUT     | STRUCT |
| `const double *values` | IN        | ARRAY  |
| `char *buffer`         | OUT       | BUFFER |
| `const char *name`     | IN        | STRING |
| `ctd_context *context` | INOUT     | OPAQUE |

Qualifiers alone are not enough to infer the contract. A non-const pointer may be logically input-only, and an output pointer may require initialized storage. Therefore, direction must be documented explicitly.

---

#####  6. Error-reporting patterns

Your example suite should include a small number of sanctioned error models.

######  Status return plus output arguments

```c
ctd_status ctd_parse_int(
    const char *text,
    int *result
);
```

This should probably be the preferred general pattern.

######  Sentinel return

```c
const char *ctd_lookup_name(int id);
```

Returns `NULL` when not found.

Suitable when the sentinel is unambiguous.

######  Boolean success return

```c
bool ctd_try_parse_int(
    const char *text,
    int *result
);
```

Suitable for simple success/failure cases without detailed diagnostics.

######  Count or signed error return

```c
ptrdiff_t ctd_decode(
    const unsigned char *input,
    size_t input_size,
    unsigned char *output,
    size_t output_capacity
);
```

This is common C, but less self-describing. Support it only where documented clearly.

I would exclude global `errno`-style error handling from the initial profile unless a target library already uses it.

---

#####  7. Patterns that should be explicitly out of scope

A strong scope definition is partly an exclusion list.

For the first version, exclude:

* callbacks from C into Python;
* function pointers as ordinary data;
* variadic functions;
* asynchronous retention of Python/CFFI-owned pointers;
* threads started by C that interact with Python objects;
* signal handlers;
* direct hardware access;
* memory-mapped I/O;
* process management;
* environment mutation;
* file-descriptor ownership protocols;
* arbitrary nested pointer graphs;
* self-referential structures requiring graph traversal;
* unions unless specifically modelled;
* bit-fields unless specifically needed;
* flexible-array-member allocation;
* custom allocators without a matching documented deallocator;
* ownership that depends on undocumented global state;
* returned pointers whose lifetime cannot be established;
* APIs requiring Python to infer buffer sizes from undocumented conventions;
* APIs that intentionally type-pun or violate ordinary C aliasing rules;
* macros as callable interfaces;
* testing inaccessible `static` functions unless the build deliberately exposes them.

This does not say such code cannot be tested. It says it is outside the reusable few-shot profile and requires target-specific work.

---

#### Recommended canonical pattern catalogue

You do not need dozens of tiny functions. A compact but systematic suite could contain approximately these examples:

1. Scalar input and scalar return.
2. Multiple scalar inputs and floating return.
3. Enum/status return.
4. Scalar out parameter.
5. Scalar inout parameter.
6. Null-terminated UTF-8 input.
7. Explicit-length byte input.
8. Borrowed returned string.
9. Owned returned string with deallocator.
10. Caller-provided output string buffer.
11. Read-only numeric input array.
12. Mutable numeric array.
13. Caller-provided output array.
14. Borrowed returned array plus count.
15. Owned returned array plus count and deallocator.
16. Structure by value.
17. Structure return by value.
18. Structure input pointer.
19. Structure inout pointer.
20. Caller-allocated output structure.
21. Borrowed returned structure pointer.
22. Owned or opaque object lifecycle.
23. Nullable pointer input.
24. Failure path preserving or resetting output arguments.
25. Capacity failure and required-size reporting.

That is already a broad practical coverage set.

---

#### The central ownership rules

I recommend making these rules foundational.

##### Caller-owned input

Memory allocated using `ffi.new()` remains owned by the Python/CFFI side.

The C function may read or modify it according to the parameter direction, but may not retain the pointer after returning unless the contract explicitly establishes a longer-lived owner.

##### Borrowed C return

The C side owns the returned pointer.

Python copies the data immediately using an appropriate operation:

```python
ffi.string(pointer)
ffi.unpack(pointer, count)
```

or explicit field extraction.

Python does not free the pointer.

##### Owned C return

The C side transfers ownership to the caller.

The API must provide the exact matching deallocator, and the test must call it.

##### Caller-provided output

Python allocates storage using `ffi.new()` and passes capacity or count as required.

The C function writes only within the declared capacity.

##### No allocator mixing

Memory allocated by C is released by C.

Memory allocated using `ffi.new()` is managed by CFFI/Python and is never passed to a C deallocator.

This rule eliminates a large class of portability and CRT-boundary problems.

---

#### One important refinement: copying pointer-containing structures

Your general rule that returned data should be copied into Python-owned memory is good, but structure copying needs care.

For this structure:

```c
typedef struct ctd_result {
    int status;
    const char *message;
    const double *values;
    size_t value_count;
} ctd_result;
```

copying the structure itself does not copy the pointed-to message or array. The test must recursively copy:

```python
result = lib.ctd_get_result()

status = result.status
message = (
    None
    if result.message == ffi.NULL
    else ffi.string(result.message).decode("utf-8")
)
values = (
    []
    if result.values == ffi.NULL
    else list(ffi.unpack(result.values, result.value_count))
)
```

Therefore, your supported structure profile should distinguish:

* **plain structures** containing only scalar fields and embedded fixed arrays;
* **descriptor structures** containing pointers whose ownership and lengths require separate documentation.

I would support descriptor structures, but only through explicit per-field contracts rather than attempted generic interpretation.

---

#### Suggested final scope statement

You could formulate the project scope approximately as follows:

> The testing framework targets deterministic C APIs implementing computational algorithms and data transformations. Tests use CFFI directly through Pytest. Supported interfaces consist of scalar values, enums, null-terminated strings, explicit-length byte sequences, typed arrays, plain structures, documented descriptor structures, and opaque object handles. Pointer parameters must have explicit direction, shape, length, nullability, retention, and ownership semantics. Memory is either caller-owned, borrowed from the callee and copied immediately, or transferred by the callee and released through a documented matching C deallocator. APIs involving callbacks, asynchronous pointer retention, variadic calls, operating-system control, hardware access, undocumented pointer graphs, or ambiguous ownership are outside the standard profile and require target-specific handling.

That is sufficiently broad for a substantial portion of algorithmic C while remaining teachable to a coding agent and manageable for you.

The demo can then be reshuffled around **one module per contract family**, with each module containing C declarations, implementation, and focused Pytest examples, rather than one large procedural demonstration.
