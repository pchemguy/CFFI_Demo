# CTD Demo for CFFI

This project aims to explore the CFFI library motivated by the desire to use CFFI for Python/Pytest unit testing of C code. The role of CFFI is to provide hopefully more convenient bridge between Pytest and called C code than what is available via the Python native `ctypes` or other leading alternatives.

This project explicitly targets exploration of candidate workflows for unit testing of static/private C functions - functions not included into the public API or exported, but which may still present important internal contracts to be verified. An integral part of the project is exploration of reflection features provided by CFFI with respect to the target C code. The primary target operating system is Windows (CMD shell, not PowerShell), though the project aims to be straightforwardly adoptable to other environments as well.

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

[CFFI](https://github.com/python-cffi/cffi) provides [several modes of operation](https://cffi.readthedocs.io/en/stable/overview.html). This project primarily focuses on API level modes, which involves a two stage process: first, a Python script is used to build a native Python wrapper package. Then this package mediates C calls to the target C library. Because the ultimate objective is the use of CFFI for unit testing C sources, meaning target library sources are readily available and target library compilation is a natural constituent of the targeted workflows, the two approaches described by CFFI documentation can be used:

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

For dynamically linked mode, the library can be built using `ctd.bat` in the same directory. After execution, 
`ctd.obj`, `ctd.lib`, `ctd.exp`, and `ctd.dll`  should be created in the same directory. Python wrapper module (`*.pyd`) will be linked against `ctd.lib` and will dispatch calls to `ctd.dll`.

## CFFI Wrapper

`ctd.py` and `ctd_embed.py` in `ctd/src/ctd/` are used to build CFFI Python wrapper package. These scripts are solely responsible for building the wrapper, nothing else. `ctd.py` creates a dynamic build and must be executed after `ctd.bat`, as it requires `ctd.lib` for linking.

### Dynamically Linked

After execution of `ctd.py`, it should create in the same directory:

1. `_ctd_wrapper.c` (name is configurable in the script).
2. `_ctd_wrapper.cp###-win_amd64.pyd` - linked wrapper package.
3. `Release/` subdirectory with intermediate wrapper build artifacts (.obj, .lib, .exp)

### Statically Linked with Embedded CTD Library

Dynamical linking is probably a more natural/simpler approach. The alternative route is provided via the `ctd_embed.py` script. It does not use prebuilt `ctd.lib`, but uses the `ctd.c` source instead. The result of `ctd_embed.py` execution is similar, except that the `Release/` subdirectory will also contain the library object`ctd.obj` file.

## Running the Demo

After either statically linked or dynamically linked wrapper is built, the demo script `ctd_demo.py` can be executed, which should produce formatted console output with the results of calling `ctd` functions.

## Wrapper Building