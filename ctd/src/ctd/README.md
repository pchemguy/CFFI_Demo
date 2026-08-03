# CTD Demo for CFFI

This project aims to explore the CFFI library motivated by the desire to use CFFI for Python/Pytest unit testing of C code. The role of CFFI is to provide hopefully more convenient bridge between Pytest and called C code than what is available via the Python native `ctypes` or other leading alternatives.

This project explicitly targets exploration of candidate workflows for unit testing of static/private C functions - functions not included into the public API or exported, but which may still present important internal contracts to be verified. An integral part of the project is exploration of reflection features provided by CFFI with respect to the target C code. The primary target operating system is Windows (CMD shell, not PowerShell), though the project aims to be straightforwardly adoptable to other environments as well.

Development of both code and exploratory documentation heavily relies on AI-assisted workflows.

## Prerequisites:

Run from a shell with activated environments:

- Conda / Python
- MSVC

### Python Environment

The `/pyenv` project directory includes a scripted tools for bootstrapping the target Python environment on Windows. This project specifically follows a philosophy of never having any system-wide Python installation or any other development tools, libraries, frameworks, and so on (this approach has been previously described in two dedicated field notes [03](https://github.com/pchemguy/Field-Notes/blob/main/03-python-env-windows/README.md) and [05](https://github.com/pchemguy/Field-Notes/blob/main/05-python-pip-msvc/README.md)). The goal is rather than fighting environment issues where more than one library or tool may end up on the shell `PATH`, is to adhere to practices that greatly reduce the risks of such collisions in the first place. Each environment, including all necessary tools or libraries, can be activate via a shell script, which starts a shell and sets environment variables, none of which contaminate the root environment. 

Briefly, `Anaconda_bootstrap.yml` and `Anaconda.yml` describe Conda environment to be created. `Anaconda.bat` is responsible for driving the setup process, relying on Windows `curl.exe` and `tar.exe`, downloading any other tools or sources automatically. This script attempts to detect presence of already created Python environment and will refuse to run, if one is detected. When executed, the script will create `Anaconda` directory next to the script for the new environment.

`msbuild.bat` is a supporting script used to detect and activate MSVC environment. Normally, it is not called directly.

`conda_far.bat` is used to start an activated Python shell. This script will refuse to proceed, if Python is on the `PATH`. `conda_far.bat` is called directly (interactive mode) and may also used by used as part of other workflows, if called with the `/batch` flag. If [Far Manager](https://farmanager.com) is on the `PATH`, `conda_far.bat` should start it in the interactive mode within the activated shell.

## Project Organization

### Demo C Program

The demo program, `CTD`, consists of three modules:

- `ctd_api.h` 
- `ctd.h`
- `ctd.c`

This standalone program incorporates a variety of simple C functions with varying signatures, including numeric scalars, strings, enumerations, structures, arrays, various pointers, global variables, and memory management.