# CTD Demo for CFFI

This project aims to explore the CFFI library motivated by the desire to use CFFI for Python/Pytest unit testing of C code. The role of CFFI is to provide hopefully more convenient bridge between Pytest and called C code than what is available via the Python native `ctypes` or other leading alternatives.

This project explicitly targets exploration of candidate workflows for unit testing of static/private C functions - functions not included into the public API or exported, but which may still present important internal contracts to be verified. An integral part of the project is exploration of reflection features provided by CFFI with respect to the target C code. The primary target operating system is Windows, though the project aims to be straightforwardly adoptable to other environments as well.

Development of both code and exploratory documentation heavily relies on AI-assisted workflows.

## Prerequisites:

Run from a shell with activated environments:

- Conda / Python
- MSVC

### Python Environment

The `/pyenv` project directory includes a scripted tools for bootstrapping the target Python environment on Windows. This project specifically follows a philosophy of never having any system-wide Python installation 

## Project Organization

### Demo C Program

The demo program, `CTD`, consists of three modules:

- `ctd_api.h` 
- `ctd.h`
- `ctd.c`

This standalone program incorporates a variety of simple C functions with varying signatures, including numeric scalars, strings, enumerations, structures, arrays, various pointers, global variables, and memory management.