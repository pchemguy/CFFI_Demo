---
url: https://chatgpt.com/c/6a6dc0ea-103c-83eb-8494-e3921a7eb03d
---

## 📗 CFFI Reflection

> [!NOTE] Prompt
> 
> I have a built CFFI extensions for API out-of-line. I import ffi and lib. Now I want to reflect/introspect on, I assume, the code provided in cdef: enums, variables, typedefs/structs/unions, and functions.

Yes—but CFFI exposes two somewhat separate reflection surfaces:

* `ffi` describes **C types**.
* `lib` exposes declared **functions, constants, enumerators, and global variables**.

There is no single public API equivalent to “return the complete parsed `cdef()` AST.” Reflection is sufficient for systematic runtime inspection, but some declaration-level distinctions are lost.

### 1. Type inventory: `ffi.list_types()`

```python
typedef_names, struct_names, union_names = ffi.list_types()
```

It returns:

```python
(
    ["typedef_name", ...],
    ["struct_tag", ...],
    ["union_tag", ...],
)
```

It does **not** return separate lists for:

* enum tags;
* function declarations;
* global variables;
* constants.

For every listed type, obtain a CFFI type descriptor with `ffi.typeof()`:

```python
for name in typedef_names:
    ctype = ffi.typeof(name)

for name in struct_names:
    ctype = ffi.typeof(f"struct {name}")

for name in union_names:
    ctype = ffi.typeof(f"union {name}")
```

`ffi.list_types()` is the supported public mechanism for enumerating user-defined typedefs, struct tags, and union tags. ([CFFI][1])

---

### 2. C type descriptors

Every value returned by `ffi.typeof()` is an `ffi.CType`. The universally available attributes are:

```python
ctype.kind
ctype.cname
```

Depending on `kind`, additional attributes may include:

```python
ctype.item
ctype.length
ctype.fields
ctype.args
ctype.result
ctype.ellipsis
ctype.abi
ctype.elements
ctype.relements
```

These are the core CFFI reflection facilities. ([CFFI][1])

Typical `kind` values include:

```text
primitive
pointer
array
function
struct
union
enum
```

#### Typedefs

A typedef name does not normally produce a distinct `kind == "typedef"` layer. CFFI resolves the typedef to the underlying type:

```python
ctype = ffi.typeof("size_t")

print(ctype.kind)
print(ctype.cname)
```

Consequently:

```c
typedef unsigned long size_t;
```

might produce something conceptually like:

```text
kind  = primitive
cname = unsigned long
```

The typedef name is preserved by `ffi.list_types()`, but `ffi.typeof(name)` describes its resolved type.

That means you should retain both:

```python
typedef_name = "size_t"
resolved_type = ffi.typeof(typedef_name)
```

Do not expect the `CType` alone to tell you which typedef spelling was used.

---

### 3. Structs and unions

Given:

```c
struct Point {
    int x;
    int y;
};
```

you can inspect it with:

```python
ctype = ffi.typeof("struct Point")

print(ctype.kind)   # "struct"
print(ctype.cname)  # "struct Point"
print(ctype.fields)
```

A useful inspection pattern is:

```python
for field_name, field in ctype.fields:
    print(
        field_name,
        field.type.cname,
        field.offset,
        field.bitshift,
        field.bitsize,
    )
```

For ordinary non-bit-field members, the bit-field-related values indicate that no bit-field encoding is present.

You can also query layout directly:

```python
ffi.sizeof("struct Point")
ffi.alignof("struct Point")
ffi.offsetof("struct Point", "x")
ffi.offsetof("struct Point", "y")
```

A recursive type formatter can walk:

* `fields` for structs and unions;
* `item` for pointers and arrays;
* `args` and `result` for functions.

---

### 4. Enums

Given:

```c
enum Color {
    COLOR_RED = 1,
    COLOR_GREEN = 4,
    COLOR_BLUE = 8
};

typedef enum Color Color;
```

the typedef is discoverable through `ffi.list_types()`:

```python
ctype = ffi.typeof("Color")

print(ctype.kind)       # "enum"
print(ctype.cname)
print(ctype.elements)
print(ctype.relements)
```

The enum-specific mappings are conceptually:

```python
ctype.elements
# {1: "COLOR_RED", 4: "COLOR_GREEN", 8: "COLOR_BLUE"}

ctype.relements
# {"COLOR_RED": 1, "COLOR_GREEN": 4, "COLOR_BLUE": 8}
```

The exact behavior with duplicate enum values deserves care: the reverse and forward mappings cannot preserve a completely lossless many-names-to-one-value relationship in every representation.

#### Important enumeration limitation

`ffi.list_types()` does not return a fourth list containing enum tags.

Therefore:

```c
enum Color { ... };
```

is not independently enumerable through a dedicated public `list_enums()` API.

You can inspect it when:

* you already know the tag name:

  ```python
  ffi.typeof("enum Color")
  ```

* it has a typedef, and that typedef appears in `typedef_names`;

* it is reached recursively through another declared type.

For systematic introspection, giving every important enum a typedef is therefore practical:

```c
typedef enum Color Color;
```

---

### 5. Functions, variables, constants, and enumerators

Names exposed by `lib` can be enumerated with:

```python
names = dir(lib)
```

CFFI specifically recommends `dir(lib)` over depending on `lib.__dict__`. ([CFFI][2])

The resulting namespace can contain:

* functions;
* global variables;
* integer constants;
* enum members;
* macro constants supported by CFFI;
* internal/special Python attributes.

Filter special names first:

```python
names = [
    name
    for name in dir(lib)
    if not name.startswith("_")
]
```

However, `dir(lib)` does not directly classify each name. You must inspect it.

---

### 6. Function introspection

For an API-mode function:

```python
function = lib.some_function
ctype = ffi.typeof(function)
```

CFFI API-mode functions may be special built-in function objects rather than ordinary `cdata` objects, but `ffi.typeof()` is explicitly supported on them. ([CFFI][3])

Example:

```python
ctype = ffi.typeof(lib.calculate)

assert ctype.kind == "function"

print(ctype.cname)
print(ctype.result)
print(ctype.args)
print(ctype.ellipsis)
print(ctype.abi)
```

Inspection:

```python
def inspect_function(ffi, lib, name: str) -> None:
    function = getattr(lib, name)
    ctype = ffi.typeof(function)

    if ctype.kind != "function":
        raise TypeError(f"{name!r} is not a function")

    print(f"name:       {name}")
    print(f"type:       {ctype.cname}")
    print(f"result:     {ctype.result.cname}")
    print(f"variadic:   {ctype.ellipsis}")
    print(f"ABI:        {ctype.abi}")

    for index, argument in enumerate(ctype.args):
        print(f"argument {index}: {argument.cname}")
```

Function parameter **names** are not retained in the function `CType`; you get argument types, not the original declarator names.

For example, these are indistinguishable at that level:

```c
int add(int left, int right);
int add(int x, int y);
```

Both yield essentially:

```text
int(int, int)
```

---

### 7. Global-variable introspection

Reading a scalar global may return an ordinary Python value:

```python
value = lib.global_count
```

Therefore this is not generally sufficient:

```python
ffi.typeof(lib.global_count)
```

For variables, the robust mechanism is:

```python
address = ffi.addressof(lib, "global_count")
pointer_type = ffi.typeof(address)
variable_type = pointer_type.item
```

Example:

```python
def inspect_variable(ffi, lib, name: str) -> None:
    pointer = ffi.addressof(lib, name)
    pointer_type = ffi.typeof(pointer)

    print(f"name:  {name}")
    print(f"type:  {pointer_type.item.cname}")
    print(f"value: {getattr(lib, name)!r}")
```

`ffi.addressof(lib, name)` supports named functions and global variables. ([CFFI][1])

For an array global:

```c
extern int values[10];
```

the variable type recovered from the pointer may require attention to whether CFFI presents the address as pointer-to-array or another appropriate descriptor. Always inspect `pointer_type.cname` rather than assuming one pointer shape.

---

### 8. Constants and enum members

Constants and enumerators are generally exposed as values:

```python
lib.BUFFER_SIZE
lib.COLOR_RED
```

Typically:

```python
isinstance(lib.BUFFER_SIZE, int)
```

But an integer-valued global variable can also appear as an integer when read. Therefore Python value type alone cannot distinguish:

```c
#define BUFFER_SIZE 4096
extern int current_size;
```

The practical discriminator is addressability:

```python
ffi.addressof(lib, "current_size")  # succeeds: variable
ffi.addressof(lib, "BUFFER_SIZE")   # fails: constant
```

Thus the general classification sequence is:

1. Try `ffi.typeof(value)` and check for `kind == "function"`.
2. Try `ffi.addressof(lib, name)` to detect a global variable.
3. Treat remaining public `lib` names as constants or enum members.

CFFI does not preserve a runtime distinction between:

```c
#define RED 1
```

and:

```c
enum Color { RED = 1 };
```

when examining only `lib.RED`. To identify it specifically as an enum member, correlate the name against the `relements` mappings of known enum types.

---

### 9. Practical namespace classifier

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


SymbolKind = Literal["function", "variable", "constant"]


@dataclass(frozen=True)
class CSymbol:
    name: str
    kind: SymbolKind
    ctype: Any | None
    value: Any


def classify_lib_symbol(ffi: Any, lib: Any, name: str) -> CSymbol:
    value = getattr(lib, name)

    # API-mode functions support ffi.typeof(), even when they are not
    # ordinary CFFI cdata objects.
    try:
        value_type = ffi.typeof(value)
    except TypeError:
        value_type = None

    if value_type is not None and value_type.kind == "function":
        return CSymbol(
            name=name,
            kind="function",
            ctype=value_type,
            value=value,
        )

    # Global variables have an address. Constants and enum members do not.
    try:
        address = ffi.addressof(lib, name)
    except (AttributeError, TypeError):
        pass
    else:
        address_type = ffi.typeof(address)

        if address_type.kind != "pointer":
            raise RuntimeError(
                f"Unexpected address type for {name!r}: "
                f"{address_type.cname}"
            )

        return CSymbol(
            name=name,
            kind="variable",
            ctype=address_type.item,
            value=value,
        )

    return CSymbol(
        name=name,
        kind="constant",
        ctype=None,
        value=value,
    )


def iter_lib_symbols(ffi: Any, lib: Any):
    for name in sorted(dir(lib)):
        if name.startswith("_"):
            continue

        try:
            yield classify_lib_symbol(ffi, lib, name)
        except AttributeError:
            # Defensively handle unusual dynamically exposed attributes.
            continue
```

Usage:

```python
for symbol in iter_lib_symbols(ffi, lib):
    ctype_name = (
        symbol.ctype.cname
        if symbol.ctype is not None
        else None
    )

    print(
        symbol.kind,
        symbol.name,
        ctype_name,
        repr(symbol.value),
    )
```

#### Why constants have `ctype=None`

A constant’s exposed Python value does not necessarily preserve its exact original C declaration type.

For example, these may all appear simply as Python integers:

```c
#define SIZE 12
static const int LIMIT = 20;   /* depending on declaration/exposure */
enum Mode { MODE_A = 1 };
```

A genuine declared global object can be typed through `ffi.addressof()`. A compile-time constant usually cannot.

---

### 10. Complete type inventory

A useful first-pass collector is:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NamedCType:
    category: str
    name: str
    ctype: Any


def iter_named_types(ffi: Any):
    typedefs, structs, unions = ffi.list_types()

    for name in sorted(typedefs):
        yield NamedCType(
            category="typedef",
            name=name,
            ctype=ffi.typeof(name),
        )

    for name in sorted(structs):
        yield NamedCType(
            category="struct",
            name=name,
            ctype=ffi.typeof(f"struct {name}"),
        )

    for name in sorted(unions):
        yield NamedCType(
            category="union",
            name=name,
            ctype=ffi.typeof(f"union {name}"),
        )
```

You can derive typedef-backed enums from this:

```python
for named_type in iter_named_types(ffi):
    if (
        named_type.category == "typedef"
        and named_type.ctype.kind == "enum"
    ):
        print(named_type.name, named_type.ctype.relements)
```

Similarly, typedef-backed structs:

```python
if named_type.ctype.kind == "struct":
    ...
```

This correctly handles patterns such as:

```c
typedef struct Point Point;
typedef enum Color Color;
```

---

### 11. Recursive type inspection

A systematic inspector should model the type graph rather than just print `cname`:

```python
def describe_type(ctype: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": ctype.kind,
        "cname": ctype.cname,
    }

    if ctype.kind == "pointer":
        result["item"] = describe_type(ctype.item)

    elif ctype.kind == "array":
        result["item"] = describe_type(ctype.item)
        result["length"] = ctype.length

    elif ctype.kind == "function":
        result["result"] = describe_type(ctype.result)
        result["arguments"] = [
            describe_type(argument)
            for argument in ctype.args
        ]
        result["variadic"] = ctype.ellipsis
        result["abi"] = ctype.abi

    elif ctype.kind in {"struct", "union"}:
        result["size"] = None
        result["alignment"] = None
        result["fields"] = []

        for field_name, field in ctype.fields:
            result["fields"].append(
                {
                    "name": field_name,
                    "type": describe_type(field.type),
                    "offset": field.offset,
                    "bitshift": field.bitshift,
                    "bitsize": field.bitsize,
                }
            )

    elif ctype.kind == "enum":
        result["elements"] = dict(ctype.elements)
        result["relements"] = dict(ctype.relements)

    return result
```

Size and alignment should be calculated using the actual `ffi` object:

```python
def add_layout(ffi: Any, description: dict[str, Any], ctype: Any) -> None:
    try:
        description["size"] = ffi.sizeof(ctype)
    except (TypeError, ffi.error):
        description["size"] = None

    try:
        description["alignment"] = ffi.alignof(ctype)
    except (TypeError, ffi.error):
        description["alignment"] = None
```

---

### 12. What runtime reflection cannot recover

The imported `ffi` and `lib` do not constitute a lossless representation of the original `cdef()` text.

You generally cannot recover:

* original comments;
* source locations;
* declaration order;
* function parameter names;
* typedef spelling used inside a function declaration;
* whether an integer constant originated from `#define`, `enum`, or another supported constant declaration without correlating it with known enums;
* arbitrary C preprocessor structure;
* all named enum tags through a dedicated enumeration API;
* declarations removed or transformed during CFFI generation;
* a complete original declarator AST.

Also, `lib` represents only CFFI-exposed declarations. It is not an export-table inspector for every symbol physically present in the DLL/PYD. CFFI states that `cdef()` registers the declared types, functions, constants, and global variables; the `lib` interface exposes the declared callable/data names. ([CFFI][4])

### Recommended model

For your verification framework, use four inventories:

```text
types
    typedefs
    structs
    unions
    typedef-backed enums

symbols
    functions
    variables
    constants/enumerators
```

Then correlate constant names with enum `relements`:

```python
enum_member_names: set[str] = set()

for typedef_name in ffi.list_types()[0]:
    ctype = ffi.typeof(typedef_name)

    if ctype.kind == "enum":
        enum_member_names.update(ctype.relements)

for symbol in iter_lib_symbols(ffi, lib):
    if (
        symbol.kind == "constant"
        and symbol.name in enum_member_names
    ):
        effective_kind = "enumerator"
    else:
        effective_kind = symbol.kind
```

That gives you reliable runtime classification within CFFI’s public introspection limits.

[1]: https://cffi.readthedocs.io/en/stable/ref.html "CFFI Reference — CFFI 2.0.0 documentation"
[2]: https://cffi.readthedocs.io/en/latest/whatsnew.html "What’s New — CFFI 2.2.0.dev0 documentation"
[3]: https://cffi.readthedocs.io/en/latest/using.html "Using the ffi/lib objects — CFFI 2.0.1.dev0 documentation"
[4]: https://cffi.readthedocs.io/en/stable/overview.html "Overview — CFFI 2.1.0 documentation"

