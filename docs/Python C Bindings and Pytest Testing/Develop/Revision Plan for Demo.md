---
url: https://chatgpt.com/codex/cloud/tasks/task_e_6a744b8bd1c88324aa009608b079d368
---

# Prompt

Create a detailed plan to revise and extend the main demo involving the C library sources in `ctd.c`, `ctd.h`, and `ctd_api.h` , as well as the associated `ctd_demo.py` module.

The architectural separation, particularly `ctd.h`, vs `ctd_api.h` must remain the same: typedefs, enums, and prototypes of variables and functions go into `ctd_api.h`, which has dual use as a library component and  CFFI `ffi.cdef()` input.

The objectives and scope of the revision is outlined in the LLM analysis provided below. I want you to use the current code and revise/extend/evolve it according to this analysis.

## Additional requirements

### Content

- All typedefs, variables, enums, and functions should represent intuitive sensible concepts without unnecessary complexity, e.g., 

```c
typedef enum ctd_status {
    CTD_OK = 0,
    CTD_ERROR_NULL = 1,
    CTD_ERROR_RANGE = 2,
    CTD_ERROR_CAPACITY = 3,
    CTD_ERROR_ALLOCATION = 4,
    CTD_ERROR_DIVIDE_BY_ZERO = 5
} ctd_status;

typedef struct ctd_point {
    double x;
    double y;
} ctd_point;

CTD_API const char ctd_global_name[] = "ctd";
CTD_API const ctd_point ctd_global_origin = {0.0, 0.0};

CTD_API const char *ctd_version(void) {
    return "ctd 1.0";
}

CTD_API const char *ctd_status_name(ctd_status status) {
    switch (status) {
        case CTD_OK:
            return "CTD_OK";
        case CTD_ERROR_NULL:
            return "CTD_ERROR_NULL";
        case CTD_ERROR_RANGE:
            return "CTD_ERROR_RANGE";
        case CTD_ERROR_CAPACITY:
            return "CTD_ERROR_CAPACITY";
        case CTD_ERROR_ALLOCATION:
            return "CTD_ERROR_ALLOCATION";
        case CTD_ERROR_DIVIDE_BY_ZERO:
            return "CTD_ERROR_DIVIDE_BY_ZERO";
        default:
            return "CTD_ERROR_UNKNOWN";
    }
}

CTD_API int ctd_add(int a, int b) {
    return a + b;
}

CTD_API ctd_status ctd_ascii_upper(char *buffer, size_t capacity) {
    size_t index;

    if (buffer == NULL) {
        return CTD_ERROR_NULL;
    }

    for (index = 0; index < capacity; ++index) {
        unsigned char character = (unsigned char)buffer[index];

        if (character == '\0') {
            return CTD_OK;
        }

        if (character >= 'a' && character <= 'z') {
            buffer[index] = (char)(character - 'a' + 'A');
        }
    }

    return CTD_ERROR_CAPACITY;
}

CTD_API ctd_point ctd_point_make(double x, double y) {
    ctd_point result;

    result.x = x;
    result.y = y;

    return result;
}

CTD_API ctd_point ctd_point_add(ctd_point a, ctd_point b) {
    ctd_point result;

    result.x = a.x + b.x;
    result.y = a.y + b.y;

    return result;
}

CTD_API double ctd_point_dot(const ctd_point *a, const ctd_point *b) {
    if (a == NULL || b == NULL) {
        return 0.0;
    }

    return a->x * b->x + a->y * b->y;
}

CTD_API ctd_status ctd_point_translate(ctd_point *point, double dx, double dy) {
    if (point == NULL) {
        return CTD_ERROR_NULL;
    }

    point->x += dx;
    point->y += dy;

    return CTD_OK;
}

CTD_API void ctd_free(void *pointer) {
    free(pointer);
}

CTD_API int ctd_global_counter_increment(void) {
    ctd_global_counter += 1;
    return ctd_global_counter;
}

CTD_API double ctd_hypot_squared(double x, double y) {
    return x * x + y * y;
}
```

- Do not reduce scope of the existing code, but DO clean it up, reducing potential unnecessary duplication or inconsistencies. For example, having `ctd_add`, `ctd_subtract`, `ctd_operation_add`, and `ctd_operation_multiply` is pointless; only `ctd_add` should be kept without overcomplicating names ("ctd_operation_add" vs "ctd_add"). Likewise, 'ctd_counter_destroy' is useless, when `ctd_free` is defined.
- Ideally define a small group of topics suitable for simple and intuitive demonstration of multiple aspects, such as the case of point operation above.
- I want to have
    - 2-3 different enums (with sensible use in the demo functions);
    - 3-5 global variables and 3-5 constants of different types;
    - 5-10 structures of varying complexity.
- Advanced typedefs (I want them to see them in CFFI, but their definitions should probably be clustered in block not meant to be included into few shot examples set for LLM)
    - at least one union;
    - 2-3 typedefs defining function pointers, such as callback;
    - 2-4 typedefs involving opaque pointers and structures;
    - basic self-referential examples (such as defining file system objects or general tree nodes).

### Organization

Use "### Recommended canonical pattern catalogue" to organize `ctd.c`, `ctd.h`, and `ctd_demo.py`. Include clear comments to attribute patterns and demo code sections.

Make sure the `ctd_demo.py` is well structured rather than having one "main dump". For each pattern, define a dedicated function, that should demonstrate both normal pattern use and patterns for pytest.

---
---

# Detailed revision plan

The revision should preserve the four handwritten source modules and both CFFI API-mode build paths:

```
ctd_api.h
    → mechanically transformed by load_cdef_header()
    → FFI.cdef()
    → dynamic or embedded wrapper
    → ffi/lib
    → ctd_demo.py and Pytest examples
```

The current implementation already covers most canonical data-flow patterns, but its catalogue is uneven: it has duplicate arithmetic APIs, only two meaningful enums, four structures, an allegedly opaque type whose representation is public, callbacks mixed into the primary demo, and a single 300-line `main()`.

## 1. Define the final catalogue and API contract before editing

Create a stable inventory so the implementation does not grow into dozens of unrelated examples. Use the exact heading **“Recommended canonical pattern catalogue”** in `ctd_api.h`, `ctd.c`, `ctd.h`, and `ctd_demo.py`, with matching section order:

1. Library information, constants, and globals.
2. Scalar values, scalar out parameters, and scalar inout parameters.
3. Strings and explicit-length byte buffers.
4. Typed arrays and capacity reporting.
5. Plain structures and structure direction patterns.
6. Descriptor structures and borrowed nested data.
7. Tagged unions.
8. Owned memory and opaque object handles.
9. Advanced declarations outside the few-shot profile.

Adopt these foundational contracts throughout:

- `ffi.new()` memory is caller-owned and never passed to `ctd_free()`.
- Input pointers are borrowed only for the duration of a call.
- Borrowed C returns are copied immediately and never freed by Python.
- Owned C returns are released only through `ctd_free()`.
- Every pointer parameter documents direction, shape, nullability, length/capacity unit, retention, and ownership.
- Capacity failures do not partially write unless explicitly documented.
- Output preservation or reset behavior on every failure is explicit.
- String capacities and required sizes are bytes and include the terminating NUL.
- Typed-array capacities and counts are elements.
- The advanced declaration section remains visible to CFFI introspection but is not presented as part of the recommended reusable few-shot profile.

Suggested task: **Define the canonical CTD interface catalogue and ownership contract**

## 2. Rationalize names without losing pattern coverage

Several current functions demonstrate the same concept without adding meaningful CFFI coverage:

- `ctd_add`, `ctd_subtract`, `ctd_operation_add`, and `ctd_operation_multiply`;
- `ctd_scale_i32` and `ctd_reverse_i32` as two interchangeable array-inout examples;
- `ctd_counter_destroy` and the general `ctd_free()` for a trivial allocation with no resource-specific teardown.

Retain `ctd_add` as the representative simple integer operation. Keep `ctd_hypot_squared`, `ctd_divide`, fixed-width arithmetic, scalar out, and scalar inout functions because each exercises a distinct signature or error contract. Retain one clear mutable-array transformation, preferably scaling.

If returned function pointers remain as advanced declarations, use an enum selector and private implementation functions rather than exporting `ctd_operation_add()` and `ctd_operation_multiply()` as redundant public calls. Remove `ctd_counter_destroy()` only if the replacement opaque object owns no nested resources and is explicitly documented as compatible with `ctd_free()`.

Suggested task: **Consolidate redundant CTD operations while preserving CFFI coverage**

## 3. Establish a coherent type model

A suitable final type inventory would be:

### Enums: three

- `ctd_status`: detailed error/status results.
- `ctd_value_kind`: discriminant for the tagged numeric union.
- `ctd_operation`: named selection for an operation or transform; use it in a real function rather than exposing an ornamental enum.

### Structures: eight or nine

Primary catalogue:

1. `ctd_point` — small plain structure, pass and return by value.
2. `ctd_range` — two scalar bounds, useful as a nullable structure input.
3. `ctd_stats` — caller-allocated output structure.
4. `ctd_record` — embedded fixed-size string and numeric array.
5. `ctd_config` — borrowed, read-only structure returned by pointer.
6. `ctd_result` — descriptor with borrowed `message`, borrowed `values`, and `value_count`.
7. `ctd_value` — tagged structure containing the union.

Advanced catalogue:

8. `ctd_node` — basic self-referential structure.
9. One truly opaque state object such as `ctd_accumulator` or `ctd_context`.

The current `struct ctd_counter` is not opaque because its field definition appears in `ctd_api.h`. Replace it with a forward declaration in `ctd_api.h` and put its representation in `ctd.c`, or rename it to a public plain structure and introduce a separate genuinely opaque object.

### Advanced declarations

- Keep `ctd_number` as the required union.
- Provide two or three function-pointer typedefs with distinct signatures, such as binary operation, numeric predicate, and node visitor.
- Provide two to four forward-declared opaque/self-referential types.
- Do not require Python callbacks in the canonical few-shot functions; declarations and an explicitly advanced diagnostic demo are enough to make the types visible through CFFI.

Suggested task: **Expand CTD into a coherent enum and structure model**

## 4. Bring globals and constants into the requested range

The current source has one mutable global and three constants if the string and point are counted as constants. Expand this deliberately rather than adding arbitrary values.

A coherent set could be:

### Mutable globals: three or four

- `int ctd_global_counter`
- `ctd_status ctd_global_last_status` 
- `double ctd_global_scale`
- optional `_Bool ctd_global_enabled`

### Read-only constants: four

- `const int ctd_global_max_points`
- `const double ctd_global_epsilon`
- `const char ctd_global_name[]`
- `const ctd_point ctd_global_origin`

Keep mutation functions deterministic. The demo should reset mutable state before and after using it so repeated runs and test order do not affect results.

Suggested task: **Add a balanced set of meaningful CTD globals and constants**

## 5. Complete the 25 canonical data-flow patterns with minimal APIs

Map the canonical patterns to a compact set rather than one function per bullet:

- Scalars: `ctd_add`, `ctd_negate_i32`, `ctd_add_u64`, `ctd_hypot_squared`.    
- Status plus scalar out: `ctd_divide`.
- Scalar out/inout: `ctd_get_magic`, `ctd_increment`.
- UTF-8 input: rename `ctd_string_length` to `ctd_utf8_length` only if it actually counts UTF-8 code points; otherwise call it `ctd_utf8_size` and document that it counts bytes.
- Explicit byte input: add a deterministic checksum and retain byte-buffer copy or XOR.
- Borrowed string: `ctd_status_name` or `ctd_version`.
- Owned string: retain the greeting/format allocation plus `ctd_free`.
- Caller string buffer: retain `ctd_copy_string` or evolve it into integer formatting with required-size reporting.
- Read-only array: sum/statistics.
- Mutable array: scale.
- Caller output array: sequence with `required_count`.
- Borrowed array: add static coefficients with output count.
- Owned array: allocated sequence with documented count.
- Structures: point by value, point return, point pointer, point inout, stats/record output, default config borrowed return.
- Descriptor: borrowed static result whose nested pointer fields are copied separately.
- Opaque lifecycle: create/get/add/free.
- Failure behavior: demonstrate null, divide-by-zero, capacity, and output-preservation cases.
    

Avoid unsafe signed overflow. In particular, sequence generation and integer scaling need preflight range checks or a narrower documented input domain before arithmetic occurs.

Suggested task: **Complete the canonical CFFI data-flow and ownership patterns**

## 6. Keep `ctd_api.h` mechanically consumable

New declarations must not introduce includes, conditional compilation, macro-expanded constants, inline implementations, or compiler attributes into the CDEF input. `ctd.h` should continue to provide standard headers, `CTD_API`, C++ linkage guards, and implementation-only macros before including `ctd_api.h`.

The duplicated `load_cdef_header()` functions in the dynamic and embedded builders are relevant because a larger type catalogue will stress their transformation. They should produce identical declaration text, but redesigning the builders is not necessary for the demo revision. At minimum, add static tests for the transformation and parse the resulting text with `FFI.cdef()`.

Suggested task: **Preserve and verify the dual-use C and CDEF header boundary**

## 7. Refactor `ctd_demo.py` into one function per contract family

Replace the current monolithic `main()` with focused functions such as:

```python
def demo_library_information() -> None: ...
def demo_scalars() -> None: ...
def demo_strings_and_bytes() -> None: ...
def demo_arrays() -> None: ...
def demo_plain_structures() -> None: ...
def demo_descriptor_structures() -> None: ...
def demo_owned_memory() -> None: ...
def demo_opaque_handles() -> None: ...
def demo_advanced_types() -> None: ...
```

Each function should show:

1. A normal successful call.
2. The exact CFFI allocation/copy idiom.
3. One representative failure or boundary case.
4. A short `pytest`-style assertion pattern.

Do not import `pytest` into the ordinary demo merely for `approx`; use direct values or `math.isclose()` in executable demo checks, while real tests use `pytest.approx()`. Prefer `ffi.unpack()` for arrays and `ffi.string()` for strings. For descriptor structures, copy nested fields explicitly.

Keep `main()` as a small ordered dispatcher. Use `try/finally` for ownership demonstrations, even if an additional `ffi.gc()` example is mentioned.

Suggested task: **Split the CTD demo into focused normal-use and Pytest pattern functions**

## 8. Add real Pytest coverage rather than treating console output as validation

`ctd/tests/` currently contains only `__init__.py`. The revised demo should be accompanied by focused tests organized by the same contract families. Because both builders produce the same `_ctd_wrapper` module name, validate modes sequentially rather than importing two same-named extensions into one interpreter.

Tests should explicitly cover:

- enum values and status-name fallbacks;
- constants and resettable globals;
- exact and approximate scalar results;
- output preservation on failures;
- null-pointer and zero-count rules;
- embedded zero bytes;
- capacity queries with unchanged destination buffers;
- borrowed return copying;
- owned return deallocation;
- structure by-value and pointer behavior;
- recursive descriptor copying;
- tagged-union discriminants;
- opaque handle lifecycle;
- CDEF visibility of advanced typedefs.

Suggested task: **Add contract-family Pytest coverage for both wrapper modes**

## 9. Synchronize documentation and introspection expectations

The README currently describes the high-level architecture but not the proposed ownership profile. Add a concise catalogue and make clear that advanced callbacks, function pointers, unions, opaque declarations, and self-referential types are retained for reflection/diagnostic study rather than promoted as generic few-shot testing patterns.

Because the exposed CDEF model will change substantially, run the introspection path and ensure deterministic serialization still handles unions, function-pointer typedefs, incomplete structures, self-references, global arrays, and descriptor fields. A schema change should not be necessary.

Suggested task: **Document the canonical profile and validate CFFI introspection**

## 10. Validation sequence

Implementation should be validated in this order on Linux:

1. Static CDEF transformation tests.
2. Standalone CTD shared-library build.
3. Dynamically linked wrapper build.
4. Demo and Pytest suite against the dynamic wrapper.
5. Clean/rebuild the wrapper in embedded mode.
6. Demo and the same Pytest suite against the embedded wrapper.
7. Introspection diagnostics.
8. Ruff and mypy for changed Python modules.
9. A warning-clean native compile where the active compiler supports the relevant warning flags.
10. Windows/MSVC validation reported separately, without assuming Linux artifacts prove Windows behavior.

Suggested task: **Validate dynamic and embedded CTD workflows end to end**

---
---

# Plan Addendum

These requirements should **replace and strengthen** the testing and documentation portions of the preceding plan.

The repository is already configured to discover tests beneath `ctd/tests`, and Pytest is an explicit project dependency.  However, the test directory currently contains no substantive test modules, so the implementation must add real, instructional Pytest examples rather than relying on `ctd_demo.py` output.

The README should be treated as source material rather than a document to patch incrementally. It currently mixes project motivation, Windows environment bootstrap details, CFFI concepts, build instructions, static-function testing, and introspection in a rough narrative.  It also describes several build artifacts predominantly from a Windows perspective even though the repository supports Linux workflows.  A complete rewrite is therefore appropriate.

## 1. Replace the testing work package with an instructional Pytest suite

The Pytest files should serve two purposes simultaneously:

1. Verify CTD behavior.
2. Act as practical, copyable examples for agents or developers testing comparable C APIs directly through CFFI.

Tests should not merely mirror each call in the demo. They should demonstrate the Pytest tools that make CFFI tests maintainable:

- `@pytest.mark.parametrize`;
- fixtures;
- fixture scopes;
- `yield` fixtures for cleanup;
- indirect parametrization where useful;
- descriptive test IDs;
- `pytest.approx`;
- exception-safe C-owned memory cleanup;
- sentinel initialization for failure-path checks;
- parametrized null/capacity/boundary cases;
- reusable assertion helpers;
- test isolation for mutable C globals.

The suite should remain easy to read. Avoid introducing dynamic test generation, custom plugins, or complex class hierarchies.

### Proposed test layout

```text
ctd/tests/
├── conftest.py
├── test_cdef_header.py
├── test_information_and_globals.py
├── test_scalars.py
├── test_strings_and_bytes.py
├── test_arrays.py
├── test_structures.py
├── test_owned_memory.py
├── test_opaque_handles.py
└── test_advanced_types.py
```

If this proves too fragmented, closely related files may be combined, but the suite should retain visible contract-family organization.

Suggested task: **Build an instructional Pytest suite around practical CFFI testing patterns**

## 2. Make parametrization demonstrate contracts, not just reduce repetition

Parametrization should highlight dimensions of the C interface:

|Test dimension|Representative parametrization|
|---|---|
|Value domain|negative, zero, positive, maximum-adjacent|
|Pointer nullability|non-NULL, NULL with zero count, NULL with nonzero count|
|Direction|output sentinel, successful write, preserved-on-error|
|Capacity|query, insufficient by one, exact, excess|
|Ownership|borrowed string, owned string, caller buffer|
|Structure passage|by value, pointer input, pointer inout|
|Enum handling|every valid member plus unknown integer|
|Byte/text distinction|ASCII text, UTF-8 bytes, embedded NUL bytes|
|Array shape|empty, singleton, multiple elements|
|Floating comparison|exact zero and `pytest.approx()` noninteger results|

Do not combine too many dimensions into one Cartesian product. Separate tests when a parameter table becomes difficult to interpret.

Suggested task: **Use Pytest parametrization to express CTD contract dimensions**

## 3. Test dynamic and embedded wrappers with the same suite

Both build modes intentionally expose the same `_ctd_wrapper` module name. Running both implementations in the same Python process risks module caching and native-extension reuse. The validation plan should therefore build and test them in separate subprocess invocations.

Do not parameterize a fixture over “dynamic” and “embedded” if doing so would require unloading and reimporting a native extension in one interpreter. The build mode is an external validation matrix, not an ordinary unit-test parameter.

Suggested task: **Run the same Pytest suite safely against both wrapper build modes**

## 4. Add focused CDEF transformation tests

The dual-use header is central to the architecture and should receive its own pure tests. These tests do not need a compiled wrapper and should therefore run before native compilation.

The dynamic and embedded builders currently share the architectural expectation that declarations originate in `ctd_api.h`, while the C compiler sees that file through `ctd.h`. The rewritten README must explain this accurately rather than suggesting that `cdef()` follows C includes.

Suggested task: **Add parametrized tests for the dual-use header transformation**

## 5. Completely rewrite the README

Do not preserve the present README section structure merely to minimize the diff. Preserve technically correct facts and important project intent, but rewrite the document into a concise, authoritative guide.

The existing README correctly identifies the two CFFI API-mode approaches, but the presentation needs cleaner terminology and platform-neutral instructions.  Its explanation of the split headers also contains an apparent wording error—`ctd_api.h` is said to be included in itself rather than in `ctd.h`—which should disappear in the rewrite. 

### Proposed README structure

```markdown
# Testing C with CFFI and Pytest

## Project objective
## Supported interface profile
## Canonical pattern catalogue
## Ownership and pointer contracts
### Caller-owned input
### Borrowed C returns
### Owned C returns
### Caller-provided output
### No allocator mixing
## CTD source architecture
### ctd_api.h
### ctd.h
### ctd.c
### ctd_demo.py
## Dual-use C/CDEF header workflow
## CTD type and API catalogue
## CFFI API-mode build strategies
### Dynamically linked wrapper
### Embedded wrapper
## Environment setup
### Cloud/Linux
### Local Windows
## Build and run
### Dynamic workflow
### Embedded workflow
## Pytest examples
### Parametrized scalar/status tests
### Capacity and output-preservation tests
### Borrowed data tests
### Owned allocation cleanup
### Structure and opaque-handle tests
## Testing private/internal C functions
## CFFI reflection and SQLite introspection
## Supported and advanced patterns
## Explicit non-goals
## Generated artifacts and cleanup
## Repository layout
```

The README should be self-contained enough that a reader can understand the experiment without reading `AGENTS.md`.

Suggested task: **Rewrite README as the authoritative CTD and CFFI testing guide**

## 6. Keep test code and README examples synchronized

Because the README is intended to teach practical Pytest patterns, its snippets must be copied from or closely track executable tests. Avoid polished pseudo-code that silently differs from the actual API.

A good policy is:

- short illustrative snippets in README;
- full executable form in `ctd/tests`;
- comments in the tests explaining the CFFI-specific reason for the pattern;
- links from documentation to exact test modules.

Suggested task: **Keep README Pytest examples aligned with executable tests**

## 7. Revised validation expectations

The implementation phase should validate both behavior and instructional quality:

1. Run pure CDEF transformation tests.
2. Build and test the dynamic wrapper in a fresh process.
3. Run the refactored demo.
4. Run the complete Pytest suite and inspect collected test IDs.
5. Build and test the embedded wrapper in a fresh process.
6. Run the same demo and Pytest suite.
7. Run introspection.
8. Run Ruff and mypy.
9. Verify every README command from its documented working directory.
10. Verify README symbols and test snippets against the final API.

`pytest --collect-only` is useful here because descriptive parametrization IDs are part of the documentation quality, not merely cosmetic output.

Suggested task: **Validate executable tests, parametrization IDs, and rewritten documentation**
