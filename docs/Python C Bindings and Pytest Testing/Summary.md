# Project Summary (512 chars max)

An exploratory CFFI project evaluating a workflow for unit-testing both exported and normally private C library functions from Python via Pytest. Static functions use a configurable `CTD_API` macro instead of the literal `static` qualifier, allowing production builds to retain internal linkage while dedicated test builds export selected functions. The project also investigates CFFI-based introspection, binding generation, and automated verification of C types, constants, variables, and functions.
