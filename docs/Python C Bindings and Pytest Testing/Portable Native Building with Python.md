---
url: https://chatgpt.com/c/6a717551-16c0-83ed-9f08-18ac9077ee33
---

## 📗 Setuptools-Distutils 

> [!NOTE] Prompt
> 
> How does ffibuilder.compile work? I want to replace my .bat cl script with platform independent python similar to ffibuilder.compile for ctd.c -> ctd.lib -> ctd.dll and .so on other systems. I also want possibly define cl specific flags when python uses msvc 

`ffibuilder.compile()` is not a general-purpose C-library build function. In CFFI out-of-line API mode, it:

1. Generates a C source file containing the CFFI/Python wrapper.
2. Selects the platform compiler through the Python packaging toolchain.
3. Compiles the generated wrapper and any `sources=[...]`.
4. Links everything into an importable Python extension:

   * Windows: `_ctd_wrapper.pyd`
   * Linux: `_ctd_wrapper.<abi>.so`
   * macOS: `_ctd_wrapper.<abi>.so`

The arguments supplied to `set_source()`—`sources`, `include_dirs`, `libraries`, `library_dirs`, `define_macros`, `extra_compile_args`, and `extra_link_args`—are largely modeled on `setuptools.Extension`. ([CFFI][1])

For example:

```python
ffibuilder.set_source(
    "_ctd_wrapper",
    '#include "ctd.h"',
    sources=["src/ctd.c"],
    include_dirs=["include"],
    define_macros=[("CTD_BUILD_LIB", "1")],
    extra_compile_args=["..."],
)
```

would compile `ctd.c` directly into `_ctd_wrapper`. It would **not** create a separate `ctd.dll`.

### Your desired build graph

There is one important correction:

```text
ctd.c -> ctd.lib -> ctd.dll
```

is not the normal MSVC DLL build graph.

Normally it is:

```text
ctd.c
  |
  v
ctd.obj
  |
  +--------> ctd.dll
  |
  +--------> ctd.lib   import library
  |
  +--------> ctd.exp
```

The `ctd.lib` generated while linking `ctd.dll` is usually an **import library**, not a static library containing the implementation.

A separate static-library build would instead be:

```text
ctd.c -> ctd.obj -> ctd_static.lib
```

On Unix-like systems, the corresponding artifacts are normally:

```text
ctd.c -> ctd.o -> libctd.so
ctd.c -> ctd.o -> libctd.a
```

You should therefore decide whether you need:

* only the shared library;
* shared library plus its Windows import library;
* or both a shared library and an independently usable static library.

For your CFFI API-mode project, the usual arrangement is:

```text
ctd.dll / libctd.so
        ^
        |
_ctd_wrapper.pyd / _ctd_wrapper.so
```

The CFFI wrapper links against `ctd.lib` on Windows or `libctd.so`/`libctd.a` on Unix.

### Portable Python build script

The closest low-level equivalent to what CFFI uses is the compiler abstraction currently supplied by Setuptools’ vendored Distutils implementation.

```python
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from setuptools._distutils.ccompiler import new_compiler
from setuptools._distutils.sysconfig import customize_compiler


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "src" / "ctd.c"
INCLUDE_DIR = ROOT / "include"
BUILD_DIR = ROOT / "build"
OBJECT_DIR = BUILD_DIR / "obj"
LIB_DIR = BUILD_DIR / "lib"
BIN_DIR = BUILD_DIR / "bin"


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def build(*, clean: bool = False, debug: bool = False) -> None:
    if clean:
        remove_tree(BUILD_DIR)

    OBJECT_DIR.mkdir(parents=True, exist_ok=True)
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    compiler = new_compiler()
    customize_compiler(compiler)

    compiler_type = compiler.compiler_type
    print(f"Compiler type: {compiler_type}")

    macros: list[tuple[str, str | None]] = [
        ("CTD_C_API", "1"),
        ("CTD_BUILD_LIB", "1"),
    ]

    extra_compile_args: list[str]
    extra_link_args: list[str]

    if compiler_type == "msvc":
        extra_compile_args = [
            "/TC",
            "/W4",
            "/permissive-",
        ]

        if not debug:
            extra_compile_args.append("/O2")

        extra_link_args = []

    elif compiler_type == "unix":
        extra_compile_args = [
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
        ]

        if not debug:
            extra_compile_args.append("-O2")

        # Required when the same objects might be linked into a shared object.
        extra_compile_args.append("-fPIC")

        extra_link_args = []

    else:
        raise RuntimeError(
            f"Unsupported compiler type: {compiler_type!r}"
        )

    objects = compiler.compile(
        sources=[os.fspath(SOURCE)],
        output_dir=os.fspath(OBJECT_DIR),
        include_dirs=[os.fspath(INCLUDE_DIR)],
        macros=macros,
        debug=debug,
        extra_postargs=extra_compile_args,
    )

    print("Objects:")
    for object_path in objects:
        print(f"  {object_path}")

    # Independent static library:
    #
    # Windows: build/lib/ctd_static.lib
    # Unix:    build/lib/libctd_static.a
    compiler.create_static_lib(
        objects=objects,
        output_libname="ctd_static",
        output_dir=os.fspath(LIB_DIR),
        debug=debug,
    )

    # Shared library:
    #
    # Windows: build/bin/ctd.dll, normally with an import library
    # Unix:    build/bin/libctd.so
    shared_name = "ctd"

    compiler.link_shared_object(
        objects=objects,
        output_filename=compiler.shared_object_filename(
            shared_name,
            output_dir=os.fspath(BIN_DIR),
        ),
        libraries=[],
        library_dirs=[],
        runtime_library_dirs=[],
        debug=debug,
        extra_postargs=extra_link_args,
        target_lang="c",
    )


def main() -> int:
    build(
        clean="--clean" in sys.argv,
        debug="--debug" in sys.argv,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run it with:

```cmd
python build_ctd.py --clean
```

or:

```cmd
python build_ctd.py --clean --debug
```

### Compiler-specific flags

The key discriminator is:

```python
compiler.compiler_type
```

Typical values are:

```python
"msvc"
"unix"
"mingw32"
"cygwin"
```

Therefore this is the appropriate pattern:

```python
if compiler.compiler_type == "msvc":
    compile_args = ["/TC", "/W4", "/O2"]
elif compiler.compiler_type == "unix":
    compile_args = ["-std=c11", "-Wall", "-Wextra", "-O2", "-fPIC"]
else:
    raise RuntimeError(...)
```

This is better than checking `sys.platform`, because the operating system does not completely determine the compiler. Windows might use MSVC, MinGW GCC, or Clang.

### MSVC discovery and activation

On Windows, the compiler abstraction can generally locate an installed Visual Studio or Build Tools installation and construct the required environment. It does not necessarily require your `.bat` activation script.

When Python is already running inside a correctly activated MSVC environment, this setting can prevent Distutils/Setuptools from trying to rediscover and reactivate MSVC:

```cmd
set DISTUTILS_USE_SDK=1
python build_ctd.py
```

Usually it is paired with:

```cmd
set MSSdk=1
```

From Python, before creating the compiler:

```python
if os.name == "nt" and os.environ.get("VSCMD_VER"):
    os.environ.setdefault("DISTUTILS_USE_SDK", "1")
    os.environ.setdefault("MSSdk", "1")
```

That gives you two modes:

* ordinary shell: Setuptools discovers MSVC;
* already activated shell: reuse the existing MSVC environment.

### Output-name complication on Windows

The low-level compiler abstraction is not especially elegant about controlling every auxiliary MSVC artifact. In particular, when linking `ctd.dll`, MSVC ordinarily creates an import library named `ctd.lib`.

That is why the independent static library in the example is called:

```text
ctd_static.lib
```

Do not attempt to put both of these in the same directory under the name `ctd.lib`:

```text
ctd.lib    static implementation library
ctd.lib    DLL import library
```

They are different artifacts with the same conventional filename.

A clean layout is:

```text
build/
    bin/
        ctd.dll
    lib/
        ctd.lib
        ctd_static.lib
    obj/
        ...
```

However, the exact location in which the MSVC compiler class emits the import library may require either:

* moving it after linking;
* passing an MSVC-specific `/IMPLIB:path`;
* or customizing the linker invocation.

### Integration with the CFFI builder

Once `ctd.dll` or `libctd.so` exists, the CFFI builder can link against it:

```python
from cffi import FFI

ffibuilder = FFI()

ffibuilder.cdef("""
    int ctd_add(int a, int b);
""")

ffibuilder.set_source(
    "_ctd_wrapper",
    '#include "ctd.h"',
    include_dirs=["include"],
    library_dirs=["build/lib", "build/bin"],
    libraries=["ctd"],
)

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
```

On Windows, `libraries=["ctd"]` means the linker looks for `ctd.lib`. At runtime, `ctd.dll` must be discoverable.

On Linux, it generally means the linker looks for:

```text
libctd.so
libctd.a
```

CFFI itself also supports putting `ctd.c` in `sources=[...]`, which avoids the standalone library completely:

```python
ffibuilder.set_source(
    "_ctd_wrapper",
    '#include "ctd.h"',
    sources=["src/ctd.c"],
    include_dirs=["include"],
    define_macros=[
        ("CTD_C_API", "1"),
        ("CTD_C_API_DEFAULT", "1"),
    ],
)
```

That architecture is simpler, but it means `_ctd_wrapper` contains its own compiled copy of `ctd.c`; no independently usable `ctd.dll` is produced. CFFI explicitly documents `sources=[...]` as a supported way to compile additional C implementation files into the extension. ([CFFI][2])

For your project, I would keep the two phases distinct:

```text
build_ctd.py
    -> ctd.dll / libctd.so
    -> ctd.lib on Windows

build_cffi.py
    -> _ctd_wrapper.pyd / _ctd_wrapper.so
    -> links against ctd
```

That preserves the real shared-library boundary you are trying to test.

[1]: https://cffi.readthedocs.io/en/latest/cdef.html "Preparing Wrapper Modules — CFFI 2.2.0.dev0 documentation"
[2]: https://cffi.readthedocs.io/en/stable/overview.html "Overview — CFFI 2.1.0 documentation"
[3]: https://setuptools.pypa.io "Setuptools"

---
---
## 📗 Shared and Static Libs - Setuptools-Distutils

> [!NOTE] Prompt
> 
> I want both static and shared lib. I suppose msvc can use either import or static? I do not need to hear more about cffi here. Focus on just build pipeline and its portable implantation via a python script with optional msvc flags

Yes. With MSVC, a consuming program links against a `.lib` in either case:

* **Static library**: contains the compiled implementation object code.
* **Import library**: contains references to exported symbols in the DLL; the implementation remains in `ctd.dll`.

The linker distinguishes them by their contents, not their extension. They therefore require different filenames or directories. A practical naming scheme is:

```text
Windows:
    lib/ctd_static.lib
    lib/ctd.lib          # import library
    bin/ctd.dll

Linux:
    lib/libctd.a
    lib/libctd.so

macOS:
    lib/libctd.a
    lib/libctd.dylib
```

When MSVC links a DLL containing exported symbols, it normally creates the import `.lib` automatically. `/IMPLIB:<path>` controls its path and name. ([Microsoft Learn][1])

### Recommended pipeline

Compile the source separately for each library:

```text
ctd.c --static macros--> ctd_static.obj/o --> static library
ctd.c --shared macros--> ctd_shared.obj/o --> DLL/shared object
```

Separate compilation matters because your header presumably gives the shared build `__declspec(dllexport)`, while the static build should not use DLL import/export semantics.

### Portable `build.py`

```python
from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from setuptools._distutils.ccompiler import CCompiler, new_compiler
from setuptools._distutils.sysconfig import customize_compiler


ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "src" / "ctd.c"
INCLUDE_DIR = ROOT / "include"

BUILD_DIR = ROOT / "build"
STATIC_OBJECT_DIR = BUILD_DIR / "obj" / "static"
SHARED_OBJECT_DIR = BUILD_DIR / "obj" / "shared"
LIBRARY_DIR = BUILD_DIR / "lib"
BINARY_DIR = BUILD_DIR / "bin"


@dataclass(frozen=True)
class BuildOptions:
    debug: bool
    clean: bool
    verbose: bool
    msvc_compile_flags: tuple[str, ...]
    msvc_link_flags: tuple[str, ...]


def parse_args(argv: Sequence[str] | None = None) -> BuildOptions:
    parser = argparse.ArgumentParser(
        description="Build static and shared versions of the CTD library."
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Build with debug information and without release optimization.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the build directory before building.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print compiler commands.",
    )
    parser.add_argument(
        "--msvc-compile-flag",
        action="append",
        default=[],
        metavar="FLAG",
        help="Append an MSVC-only compiler flag; may be specified repeatedly.",
    )
    parser.add_argument(
        "--msvc-link-flag",
        action="append",
        default=[],
        metavar="FLAG",
        help="Append an MSVC-only linker flag; may be specified repeatedly.",
    )

    args = parser.parse_args(argv)

    return BuildOptions(
        debug=args.debug,
        clean=args.clean,
        verbose=args.verbose,
        msvc_compile_flags=tuple(args.msvc_compile_flag),
        msvc_link_flags=tuple(args.msvc_link_flag),
    )


def create_compiler(*, verbose: bool) -> CCompiler:
    compiler = new_compiler(verbose=int(verbose))
    customize_compiler(compiler)
    return compiler


def prepare_directories(*, clean: bool) -> None:
    if clean and BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    STATIC_OBJECT_DIR.mkdir(parents=True, exist_ok=True)
    SHARED_OBJECT_DIR.mkdir(parents=True, exist_ok=True)
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    BINARY_DIR.mkdir(parents=True, exist_ok=True)


def compile_flags(
    compiler: CCompiler,
    options: BuildOptions,
    *,
    shared: bool,
) -> list[str]:
    compiler_type = compiler.compiler_type

    if compiler_type == "msvc":
        flags = [
            "/TC",
            "/W4",
        ]

        if options.debug:
            flags.extend(
                [
                    "/Od",
                    "/Zi",
                ]
            )
        else:
            flags.extend(
                [
                    "/O2",
                ]
            )

        flags.extend(options.msvc_compile_flags)
        return flags

    if compiler_type in {"unix", "mingw32", "cygwin"}:
        flags = [
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
        ]

        if options.debug:
            flags.extend(
                [
                    "-O0",
                    "-g",
                ]
            )
        else:
            flags.append("-O2")

        if shared and compiler_type == "unix":
            flags.append("-fPIC")

        return flags

    raise RuntimeError(f"Unsupported compiler type: {compiler_type!r}")


def link_flags(
    compiler: CCompiler,
    options: BuildOptions,
    *,
    import_library: Path | None,
) -> list[str]:
    compiler_type = compiler.compiler_type

    if compiler_type == "msvc":
        flags = list(options.msvc_link_flags)

        if import_library is not None:
            flags.append(f"/IMPLIB:{import_library.resolve()}")

        return flags

    if compiler_type in {"unix", "mingw32", "cygwin"}:
        return []

    raise RuntimeError(f"Unsupported compiler type: {compiler_type!r}")


def compile_static_objects(
    compiler: CCompiler,
    options: BuildOptions,
) -> list[str]:
    return compiler.compile(
        sources=[os.fspath(SOURCE)],
        output_dir=os.fspath(STATIC_OBJECT_DIR),
        include_dirs=[os.fspath(INCLUDE_DIR)],
        macros=[
            ("CTD_C_API_DEFAULT", "1"),
        ],
        debug=options.debug,
        extra_postargs=compile_flags(
            compiler,
            options,
            shared=False,
        ),
    )


def compile_shared_objects(
    compiler: CCompiler,
    options: BuildOptions,
) -> list[str]:
    return compiler.compile(
        sources=[os.fspath(SOURCE)],
        output_dir=os.fspath(SHARED_OBJECT_DIR),
        include_dirs=[os.fspath(INCLUDE_DIR)],
        macros=[
            ("CTD_C_API", "1"),
            ("CTD_BUILD_LIB", "1"),
        ],
        debug=options.debug,
        extra_postargs=compile_flags(
            compiler,
            options,
            shared=True,
        ),
    )


def build_static_library(
    compiler: CCompiler,
    objects: Sequence[str],
    options: BuildOptions,
) -> Path:
    output_name = "ctd_static" if compiler.compiler_type == "msvc" else "ctd"

    compiler.create_static_lib(
        objects=list(objects),
        output_libname=output_name,
        output_dir=os.fspath(LIBRARY_DIR),
        debug=options.debug,
    )

    filename = compiler.library_filename(
        output_name,
        lib_type="static",
        output_dir=os.fspath(LIBRARY_DIR),
    )

    return Path(filename)


def shared_library_path(compiler: CCompiler) -> Path:
    if compiler.compiler_type == "msvc":
        return BINARY_DIR / "ctd.dll"

    filename = compiler.library_filename(
        "ctd",
        lib_type="shared",
        output_dir=os.fspath(LIBRARY_DIR),
    )

    return Path(filename)


def build_shared_library(
    compiler: CCompiler,
    objects: Sequence[str],
    options: BuildOptions,
) -> tuple[Path, Path | None]:
    shared_path = shared_library_path(compiler)

    import_library: Path | None

    if compiler.compiler_type == "msvc":
        import_library = LIBRARY_DIR / "ctd.lib"
    else:
        import_library = None

    compiler.link_shared_object(
        objects=list(objects),
        output_filename=os.fspath(shared_path),
        debug=options.debug,
        extra_postargs=link_flags(
            compiler,
            options,
            import_library=import_library,
        ),
        target_lang="c",
    )

    return shared_path, import_library


def print_artifact(label: str, path: Path | None) -> None:
    if path is not None:
        print(f"{label:<16} {path.resolve()}")


def main(argv: Sequence[str] | None = None) -> int:
    options = parse_args(argv)

    if not SOURCE.is_file():
        raise FileNotFoundError(f"C source file not found: {SOURCE}")

    if not INCLUDE_DIR.is_dir():
        raise FileNotFoundError(f"Include directory not found: {INCLUDE_DIR}")

    prepare_directories(clean=options.clean)

    compiler = create_compiler(verbose=options.verbose)

    print(f"Compiler type:   {compiler.compiler_type}")

    static_objects = compile_static_objects(compiler, options)
    static_library = build_static_library(
        compiler,
        static_objects,
        options,
    )

    shared_objects = compile_shared_objects(compiler, options)
    shared_library, import_library = build_shared_library(
        compiler,
        shared_objects,
        options,
    )

    print()
    print_artifact("Static library:", static_library)
    print_artifact("Shared library:", shared_library)
    print_artifact("Import library:", import_library)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The low-level compiler abstraction supplies `compile()`, `create_static_lib()`, and `link_shared_object()`, and `extra_postargs` is the intended escape hatch for compiler- or linker-specific options. ([Setuptools][2])

### Expected macro behavior

Given your existing API macro design, the two builds should resolve approximately as follows.

#### Static build

```python
macros=[
    ("CTD_C_API_DEFAULT", "1"),
]
```

This should make:

```c
##define CTD_API
```

The functions have normal external linkage without `dllimport` or `dllexport`.

#### Shared build

```python
macros=[
    ("CTD_C_API", "1"),
    ("CTD_BUILD_LIB", "1"),
]
```

On Windows this should make:

```c
##define CTD_API __declspec(dllexport)
```

On GCC/Clang:

```c
##define CTD_API __attribute__((visibility("default")))
```

### Invocation examples

Release build:

```cmd
python build.py --clean
```

Debug build:

```cmd
python build.py --clean --debug
```

Show commands:

```cmd
python build.py --clean --verbose
```

Add MSVC-only options:

```cmd
python build.py --clean ^
    --msvc-compile-flag=/WX ^
    --msvc-compile-flag=/utf-8 ^
    --msvc-link-flag=/INCREMENTAL:NO
```

Because the CLI option begins with `/`, use the `=` form:

```cmd
--msvc-compile-flag=/WX
```

rather than:

```cmd
--msvc-compile-flag /WX
```

The latter can be misinterpreted by argument parsers.

### Resulting build tree

On Windows:

```text
build/
├── bin/
│   └── ctd.dll
├── lib/
│   ├── ctd.lib
│   └── ctd_static.lib
└── obj/
    ├── shared/
    │   └── ...
    └── static/
        └── ...
```

On Linux:

```text
build/
├── bin/
├── lib/
│   ├── libctd.a
│   └── libctd.so
└── obj/
    ├── shared/
    │   └── ...
    └── static/
        └── ...
```

The Python API used here is Setuptools’ retained Distutils compiler abstraction. It remains available in current Setuptools, but its documentation is categorized as legacy/deprecated. For a compact build script it is useful because it handles compiler discovery and platform filename conventions, but it should be isolated in this one script rather than treated as a stable application-level API. ([Setuptools][2])

[1]: https://learn.microsoft.com/en-us/cpp/build/reference/link-output?view=msvc-170 "LINK Output | Microsoft Learn"
[2]: https://setuptools.pypa.io/en/stable/deprecated/distutils/apiref.html "9. API Reference - setuptools 83.0.0 documentation"

---
---
## 📗 Meson and CMake

> [!NOTE] Prompt
> 
> Are there equivalent replacement options for deprecated API?

There is **no modern drop-in Python API** replacing:

```python
new_compiler()
compiler.compile()
compiler.create_static_lib()
compiler.link_shared_object()
```

PEP 632 removed `distutils` from the standard library, while Setuptools retained a vendored copy mainly for compatibility. Setuptools explicitly says that some Distutils use cases still lack suitable replacements. ([Python Enhancement Proposals (PEPs)][1])

For your requirement—building both a static and shared C library portably—the realistic replacements are build systems invoked by Python.

### Best fit: Meson

Meson is probably the closest match to your desired simplicity:

* native MSVC, GCC, Clang and MinGW support;
* automatic compiler selection;
* static and shared libraries as first-class targets;
* compiler-specific arguments;
* concise configuration;
* callable from a small Python wrapper;
* no deprecated Python compiler API.

Meson even has a dedicated `both_libraries()` operation, although its documentation generally recommends `library()` where appropriate. ([Meson Build][2])

#### `meson.build`

```meson
project(
  'ctd',
  'c',
  version: '1.0.0',
  default_options: [
    'c_std=c11',
    'warning_level=3',
  ],
)

cc = meson.get_compiler('c')

ctd_sources = files(
  'src/ctd.c',
)

ctd_include = include_directories(
  'include',
)

common_c_args = []

if cc.get_id() == 'msvc'
  common_c_args += [
    '/TC',
    '/utf-8',
  ]
elif cc.get_id() in ['gcc', 'clang']
  common_c_args += [
    '-Wall',
    '-Wextra',
    '-Wpedantic',
  ]
endif

ctd_static = static_library(
  'ctd_static',
  ctd_sources,
  include_directories: ctd_include,
  c_args: common_c_args,
  c_pch: [],
  install: false,
)

ctd_shared = shared_library(
  'ctd',
  ctd_sources,
  include_directories: ctd_include,
  c_args: common_c_args,
  c_pch: [],
  c_args: common_c_args,
  gnu_symbol_visibility: 'hidden',
  install: false,
)
```

You would normally add target-specific macros:

```meson
ctd_static = static_library(
  'ctd_static',
  ctd_sources,
  include_directories: ctd_include,
  c_args: common_c_args + [
    '-DCTD_C_API_DEFAULT=1',
  ],
)

ctd_shared = shared_library(
  'ctd',
  ctd_sources,
  include_directories: ctd_include,
  c_args: common_c_args + [
    '-DCTD_C_API=1',
    '-DCTD_BUILD_LIB=1',
  ],
)
```

A cleaner version uses Meson’s structured macro support:

```meson
static_args = common_c_args
shared_args = common_c_args

if cc.get_id() == 'msvc'
  static_args += ['/DCTD_C_API_DEFAULT=1']
  shared_args += [
    '/DCTD_C_API=1',
    '/DCTD_BUILD_LIB=1',
  ]
else
  static_args += ['-DCTD_C_API_DEFAULT=1']
  shared_args += [
    '-DCTD_C_API=1',
    '-DCTD_BUILD_LIB=1',
  ]
endif
```

Meson directly models static and shared build targets and handles PIC, import libraries, object suffixes and linker selection internally. ([Meson Build][2])

#### Python front end

```python
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from collections.abc import Sequence


ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"


def run(command: Sequence[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--msvc-compile-flag",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--msvc-link-flag",
        action="append",
        default=[],
    )
    args = parser.parse_args()

    if args.clean:
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    build_type = "debug" if args.debug else "release"

    setup_command = [
        "meson",
        "setup",
        str(BUILD_DIR),
        f"--buildtype={build_type}",
    ]

    if not BUILD_DIR.exists():
        run(setup_command)

    compile_flags = " ".join(args.msvc_compile_flag)
    link_flags = " ".join(args.msvc_link_flag)

    configure_command = [
        "meson",
        "configure",
        str(BUILD_DIR),
    ]

    if compile_flags:
        configure_command.append(f"-Dc_args={compile_flags}")

    if link_flags:
        configure_command.append(f"-Dc_link_args={link_flags}")

    if len(configure_command) > 3:
        run(configure_command)

    run(
        [
            "meson",
            "compile",
            "-C",
            str(BUILD_DIR),
        ]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

There is one caveat: setting global `c_args` from the Python CLI can replace or interact with configured arguments. For a robust implementation, define your own Meson array options instead.

#### Custom Meson options

`meson_options.txt`:

```meson
option(
  'extra_msvc_compile_args',
  type: 'array',
  value: [],
  description: 'Additional MSVC compiler arguments',
)

option(
  'extra_msvc_link_args',
  type: 'array',
  value: [],
  description: 'Additional MSVC linker arguments',
)
```

Then:

```meson
if cc.get_id() == 'msvc'
  common_c_args += get_option('extra_msvc_compile_args')
  common_link_args = get_option('extra_msvc_link_args')
else
  common_link_args = []
endif
```

Pass them from Python:

```python
setup_command.extend(
    [
        "-Dextra_msvc_compile_args=/WX,/utf-8",
        "-Dextra_msvc_link_args=/INCREMENTAL:NO",
    ]
)
```

This keeps MSVC-specific policy inside the build definition rather than forcing Python to emulate a compiler abstraction.

### Alternative: CMake

CMake is the more established and broadly integrated option.

```cmake
cmake_minimum_required(VERSION 3.20)

project(ctd LANGUAGES C)

add_library(ctd_static STATIC
    src/ctd.c
)

add_library(ctd_shared SHARED
    src/ctd.c
)

target_include_directories(ctd_static
    PUBLIC include
)

target_include_directories(ctd_shared
    PUBLIC include
)

target_compile_definitions(ctd_static
    PRIVATE CTD_C_API_DEFAULT=1
)

target_compile_definitions(ctd_shared
    PRIVATE
        CTD_C_API=1
        CTD_BUILD_LIB=1
)

if(MSVC)
    target_compile_options(ctd_static PRIVATE
        /TC
        /W4
        /utf-8
    )

    target_compile_options(ctd_shared PRIVATE
        /TC
        /W4
        /utf-8
    )
else()
    target_compile_options(ctd_static PRIVATE
        -Wall
        -Wextra
        -Wpedantic
    )

    target_compile_options(ctd_shared PRIVATE
        -Wall
        -Wextra
        -Wpedantic
    )
endif()

set_target_properties(ctd_static PROPERTIES
    OUTPUT_NAME ctd_static
)

set_target_properties(ctd_shared PROPERTIES
    OUTPUT_NAME ctd
)
```

Python wrapper:

```python
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"


def run(*args: str) -> None:
    command = list(args)
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.clean:
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    configuration = "Debug" if args.debug else "Release"

    run(
        "cmake",
        "-S",
        str(ROOT),
        "-B",
        str(BUILD_DIR),
    )

    run(
        "cmake",
        "--build",
        str(BUILD_DIR),
        "--config",
        configuration,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

For a Python package using CMake, `scikit-build-core` is the modern packaging backend. It is not necessary merely to run CMake from your own build script. ([Scikit-Build Core][3])

### Other options

#### Direct subprocess calls

You can write Python that invokes:

```text
cl.exe / lib.exe / link.exe
gcc / ar
clang / llvm-ar
```

This gives maximal control but means implementing:

* compiler detection;
* MSVC environment discovery;
* platform-specific flags;
* library naming;
* PIC handling;
* import-library generation;
* debug/release modes;
* dependency tracking;
* incremental builds.

That recreates much of a build system and is not a true replacement for the old compiler abstraction.

#### Setuptools `build_ext`

`setuptools.command.build_ext` still exposes compiler machinery indirectly, but it is oriented around Python extension modules. Its extensibility is supported, but using it to build arbitrary standalone static and shared libraries would be an awkward adaptation rather than a clean replacement. ([Setuptools][4])

#### `meson-python` or `scikit-build-core`

These are needed when the build must integrate with:

```text
pip install
python -m build
wheel creation
sdist creation
pyproject.toml
```

They are packaging backends, not substitutes for Meson or CMake themselves. `meson-python` delegates native compilation to Meson, while `scikit-build-core` delegates it to CMake. ([Meson Build][5])

### Recommendation

For your compact C project, I would use:

```text
build.py
meson.build
meson_options.txt
```

The responsibilities would be:

```text
build.py
    CLI convenience
    clean/configure/build
    optional user-supplied flags

meson.build
    static/shared targets
    compiler detection
    macros
    warnings
    optimization
    artifact naming

Meson
    MSVC/GCC/Clang invocation
    dependency tracking
    import-library creation
    PIC
    incremental rebuilds
```

Meson is substantially cleaner than relying on `setuptools._distutils`, while still keeping the project much smaller than a typical CMake setup.

[1]: https://peps.python.org/pep-0632/ "PEP 632 – Deprecate distutils module | peps.python.org"
[2]: https://mesonbuild.com/Reference-manual_functions_library.html "library()"
[3]: https://scikit-build-core.readthedocs.io/en/stable/index.html "scikit-build-core 1.0.3 documentation"
[4]: https://setuptools.pypa.io/en/stable/userguide/extension.html "Extending or Customizing Setuptools - setuptools 82.0.1 documentation"
[5]: https://mesonbuild.com/meson-python/ "meson-python"
