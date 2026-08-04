# CTD Demo for CFFI

This project aims to explore the CFFI library motivated by the desire to use CFFI for Python/Pytest unit testing of C code. The role of CFFI is to provide hopefully more convenient bridge between Pytest and called C code than what is available via the Python native `ctypes` or other leading alternatives.

This project explicitly targets exploration of candidate workflows for unit testing of static/private C functions - functions not included into the public API or exported, but which may still present important internal contracts to be verified. An integral part of the project is exploration of reflection features provided by CFFI with respect to the target C code. 

Development of both code and exploratory documentation heavily relies on AI-assisted workflows.

## Prerequisites:

Run from a shell with activated environments:

- Conda / Python
- MSVC

### Python Environment

The `/pyenv` project directory includes a scripted tools for bootstrapping the target Python environment on Windows. This project specifically follows a philosophy of never having any system-wide Python installation or any other development tools, libraries, frameworks, and so on (see also this [note](https://github.com/pchemguy/Field-Notes/blob/main/03-python-env-windows/README.md)). The goal is rather than fighting environment issues where more than one library or tool may end up on the shell `PATH`, is to adhere to practices that greatly reduce the risks of such collisions in the first place. Each environment, including all necessary tools or libraries, can be activate via a shell script, which starts a shell and sets environment variables, none of which contaminate the root environment. 

Briefly, `Anaconda_bootstrap.yml` and `Anaconda.yml` describe Conda environment to be created. `Anaconda.bat` is responsible for driving the setup process, relying on Windows `curl.exe` and `tar.exe`, downloading any other tools or sources automatically. This script attempts to detect presence of already created Python environment and will refuse to run, if one is detected. When executed, the script will create `Anaconda` directory next to the script for the new environment.

`msbuild.bat` is a supporting script used to detect and activate MSVC environment within the Python environment (see also this [note](https://github.com/pchemguy/Field-Notes/blob/main/05-python-pip-msvc/README.md)). Normally, it is not called directly.

`conda_far.bat` is used to start an activated Python shell. This script will refuse to proceed, if Python is on the `PATH`. `conda_far.bat` is called directly (interactive mode) and may also used by used as part of other workflows, if called with the `/batch` flag. If [Far Manager](https://farmanager.com) is on the `PATH`, `conda_far.bat` should start it in the interactive mode within the activated shell.

## CFFI Modes

[CFFI](https://github.com/python-cffi/cffi) provides [several modes of operation](https://cffi.readthedocs.io/en/stable/overview.html). This project primarily focuses on API level modes, which involves a two stage process: first, a Python script is used to build a native [Python wrapper module](https://cffi.readthedocs.io/en/stable/cdef.html). Then this package mediates C calls to the target C library. Because the ultimate objective is the use of CFFI for unit testing C sources, meaning target library sources are readily available and target library compilation is a natural constituent of the targeted workflows, the two approaches described by CFFI documentation can be used:

- Target library is built independently and then the wrapper package is dynamically linked against it.
- Target sources are built by the same interface used for building the wrapper package resulting in static linking, where the wrapper package embeds the target library.

Both of these approaches are explored by this project. Additionally, custom pipelines can also be defined where CFFI generates wrapper C sources, which can then be integrated into the target library build process. This approach is beyond the scope of the current project. 

## Demo C Library

The demo library, `CTD`, consists of three modules inside `ctd/src/ctd/`:

- `ctd_api.h` 
- `ctd.h`
- `ctd.c`

This standalone program incorporates a variety of simple C functions with varying signatures, including numeric scalars, strings, enumerations, structures, arrays, various pointers, global variables, and memory management.

Note, that the header file is split into two parts `ctd.h` and `ctd_api.h`, where the former includes the latter (so the `ctd.c` only includes `ctd.h` directly). The reason and principle behind this split will be provided in later parts.

For dynamically linked mode, the library can be built using `build_ctd.py` in the same directory. After execution on Widows, `ctd.lib` (import lib), `ctd.exp`, and `ctd.dll`  should be created in the same directory (static lib `ctd.lib` under `build\lib\`). Python wrapper module (`*.pyd`) will be linked against `ctd.lib` and will dispatch calls to `ctd.dll`.

## CFFI Wrapper

`build_ctd_wrapper.py` and `build_ctd_wrapper_embedded.py` in `ctd/src/ctd/` are used to build CFFI Python wrapper package. These scripts are solely responsible for building the wrapper, nothing else. `build_ctd_wrapper.py` creates a dynamic build and must be executed after `build_ctd.py`, as it requires `ctd.lib` import library (or the shared library on non-Windows systems) for linking.

### Dynamically Linked

After execution of `build_ctd_wrapper.py`, it should create in the same directory:

1. `_ctd_wrapper.c` (name is configurable in the script).
2. `_ctd_wrapper.cp###-win_amd64.pyd` (Windows) - linked wrapper package.
3. `Release/` subdirectory with intermediate wrapper build artifacts (.obj, .lib, .exp)

### Statically Linked with Embedded CTD Library

Dynamical linking is probably a more natural/simpler approach. The alternative route is provided via the `build_ctd_wrapper_embedded.py` script. It does not use prebuilt `ctd.lib`, but uses the `ctd.c` source instead. The result of `build_ctd_wrapper_embedded.py` execution is similar, except that the `Release/` subdirectory will also contain the library object `ctd.obj` file.

## Running the Demo

After either statically linked or dynamically linked wrapper is built, the demo script `ctd_demo.py` can be executed, which should produce formatted console output with the results of calling `ctd` functions.

## Wrapper Building

The two build scripts are largely similar, only differing in a few build options. The core logic is in the `main` function, which uses three CFFI methods:

1. `ffibuilder.cdef()`
2. `ffibuilder.set_source()`
3. `ffibuilder.compile()`

where `ffibuilder` is an instance of `cffi.FFI`.

The `.cdef()` method expects a single multiline string declaring the C types, functions and globals needed to be available to the Python caller. `.cdef()` input may contain valid `typedef`'s, and function and variable prototypes. It does not support any preprocessor directives, except for `#define <NAME> <INT>` (but any defined `<NAME>` cannot appear anywhere else in the input, so it is not so much a preprocessor directive, as a special syntax to define constant aliases which will be exposed via corresponding `lib.<NAME>` attribute, meaning the same namespace as function and global names). The input to `.cdef()` is parsed by the [pycparser](https://github.com/eliben/pycparser) library and determines which custom C types (typedef) can be used via the `ffi` object (standard C types can be used directly) and which C functions and globals are exposed as `lib` object attributes. 

`.set_source()` configures C build toolchain (such as MSVC on Windows). The first positional argument defines the name of the generated wrapper source and package. The second positional arguments defines a valid C snippet, which will be inserted into the wrapper source verbatim. When linking against the target library, this snippet at the minimum must include the target library's developer header, such as `#include "ctd.h"`. Because this snippet is inserted into the wrapper source, it may, in principle, contain any valid C, such as `typdef` declarations, implementation of functions and so on.

## Unit Testing Static Methods

There various approaches to testing static method based on special test builds and adapters, which enable access to otherwise inaccessible from outside `static` C functions and variables. The present approach relies on replacing explicit `static` qualification with a preprocessor macro, such as `CTD_API` (defined in `ctd.h`), which enables straightforward build-time control over whether a function `static` in production builds will be accessible in test builds.

## Dual Use (C/CDEF) Modules

One of the desired features is the ability to generate wrapping code without any manual editing of the sources and, importantly without maintaining a separate module for CFFI CDEF input. While CDEF input accepts valid C code, it does not support C macro language. To satisfy both aspects, the original `ctd.h` module has been split in two, moving part of it to `ctd_api.h`, which contains declarations to be fed to CDEF for availability in Python. The only two aspects of this module not supported by CDEF are the standard header guard wrapper and `CTD_API` part of declarations. Both components can be automatically removed from the loaded module before providing it to CDEF. The same module is included in `ctd_api.h`, so for C compiler the picture is completely equivalent to alternative with  single `ctd.h` incorporating the contents of `ctd_api.h` inline.
