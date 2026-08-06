"""
https://chatgpt.com/c/6a717551-16c0-83ed-9f08-18ac9077ee33
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from setuptools._distutils.ccompiler import CCompiler, new_compiler
from setuptools._distutils.sysconfig import customize_compiler

PREFIX = Path(__file__).resolve().parent

SOURCES = [PREFIX / "ctd.c"]
INCLUDE_DIR = PREFIX

BUILD_DIR = PREFIX / "build"
STATIC_OBJECT_DIR = BUILD_DIR / "obj" / "static"
SHARED_OBJECT_DIR = BUILD_DIR / "obj" / "shared"
LIB_DIR = BUILD_DIR / "lib"
BIN_DIR = PREFIX

LIB_NAME = "ctd"


def prepare_directories() -> None:
    STATIC_OBJECT_DIR.mkdir(parents=True, exist_ok=True)
    SHARED_OBJECT_DIR.mkdir(parents=True, exist_ok=True)
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)


def compile_flags(compiler_type: str, shared: bool) -> list[str]:
    if compiler_type == "msvc":
        flags = [
            "/TC",
            "/W4",
            "/O2",
        ]
    elif compiler_type in {"unix", "mingw32", "cygwin"}:
        flags = [
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-O2",
        ]
        if shared and compiler_type == "unix":
            flags.append("-fPIC")
    else:
        raise RuntimeError(f"Unsupported compiler type: {compiler_type!r}")

    return flags


def link_flags(compiler_type: str, import_library: Path | None) -> list[str]:
    if compiler_type == "msvc":
        if import_library is None:
            raise ValueError(
                "An import-library path is required for an MSVC shared build"
            )
        return [f"/IMPLIB:{import_library.resolve()}"]

    if compiler_type in {"unix", "mingw32", "cygwin"}:
        return []

    raise RuntimeError(f"Unsupported compiler type: {compiler_type!r}")


def macros(shared: bool) -> list[tuple[str] | tuple[str, str | None]]:
    if shared:
        macro_list: list[tuple[str] | tuple[str, str | None]] = [
            ("CTD_C_API", None),
            ("CTD_BUILD_LIB", None),
        ]
    else:
        macro_list = [("CTD_STATIC_LIB", None)]
    return macro_list


def library_path(compiler: CCompiler, shared: bool) -> Path:
    if compiler.compiler_type == "msvc":
        if shared:
            filename = BIN_DIR / f"{LIB_NAME}.dll"
        else:
            filename = LIB_DIR / f"{LIB_NAME}.lib"
    else:
        filename = compiler.library_filename(
            LIB_NAME,
            lib_type="shared" if shared else "static",
            output_dir=os.fspath(BIN_DIR if shared else LIB_DIR),
        )

    return Path(filename)


def compile_objects(compiler: CCompiler, shared: bool) -> list[str]:
    return compiler.compile(
        sources=[os.fspath(source) for source in SOURCES],
        output_dir=os.fspath(SHARED_OBJECT_DIR if shared else STATIC_OBJECT_DIR),
        include_dirs=[os.fspath(INCLUDE_DIR)],
        macros=macros(shared=shared),
        extra_postargs=compile_flags(compiler.compiler_type, shared=shared),
    )


def build_static_library(compiler: CCompiler, objects: Sequence[str]) -> Path:
    compiler.create_static_lib(
        objects=list(objects),
        output_libname=LIB_NAME,
        output_dir=os.fspath(LIB_DIR),
    )

    return library_path(compiler, shared=False)


def build_shared_library(
    compiler: CCompiler,
    objects: Sequence[str],
) -> tuple[Path, Path | None]:
    shared_path = library_path(compiler, shared=True)

    import_library: Path | None = None
    if compiler.compiler_type == "msvc":
        import_library = BIN_DIR / f"{LIB_NAME}.lib"

    compiler.link_shared_object(
        objects=list(objects),
        output_filename=os.fspath(shared_path),
        extra_postargs=link_flags(
            compiler.compiler_type,
            import_library=import_library,
        ),
        target_lang="c",
    )

    return shared_path, import_library


def print_artifact(label: str, path: Path | None) -> None:
    if path is not None:
        print(f"{label:<16} {path.resolve()}")


def main() -> int:
    for source in SOURCES:
        if not source.is_file():
            raise FileNotFoundError(f"C source file not found: {source}")

    if not INCLUDE_DIR.is_dir():
        raise FileNotFoundError(f"Include directory not found: {INCLUDE_DIR}")

    prepare_directories()

    compiler: CCompiler = new_compiler()
    customize_compiler(compiler)

    print(f"Compiler type:   {compiler.compiler_type}")

    static_objects = compile_objects(compiler, shared=False)
    static_library = build_static_library(compiler, static_objects)

    shared_objects = compile_objects(compiler, shared=True)
    shared_library, import_library = build_shared_library(compiler, shared_objects)

    print()
    print_artifact("Static library:", static_library)
    print_artifact("Shared library:", shared_library)
    print_artifact("Import library:", import_library)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
