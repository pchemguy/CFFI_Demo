/*
** ctd.h
**
** Standalone C99 DLL fixture for exploring Python CFFI.
*/

#ifndef CTD_H
#define CTD_H

#include <stddef.h>
#include <stdint.h>


/****************************** API Declaration ******************************/

/*
** ```markdown
** ## Build Modes
** 
** | Defines                       | `CTD_API`                                         |
** | ----------------------------- | ------------------------------------------------- |
** | `CTD_C_API` + `CTD_BUILD_LIB` | exported DLL/shared-library symbol                |
** | `CTD_C_API` + `CTD_BUILD_EXE` | imported DLL symbol on Windows; default elsewhere |
** | `CTD_C_API_DEFAULT`           | default declaration                               |
** | none                          | `static`                                          |
** ```
*/

#if defined(CTD_C_API)

#  if defined(CTD_BUILD_LIB)

#    if defined(_WIN32)
#      define CTD_API __declspec(dllexport)
#    elif defined(__GNUC__) || defined(__clang__)
#      define CTD_API __attribute__((visibility("default")))
#    else
#      define CTD_API
#    endif

#  elif defined(CTD_BUILD_EXE)

#    if defined(_WIN32)
#      define CTD_API __declspec(dllimport)
#    else
#      define CTD_API
#    endif

#  else
#    error "CTD_C_API requires CTD_BUILD_LIB or CTD_BUILD_EXE"
#  endif

#elif defined(CTD_C_API_DEFAULT)

#  define CTD_API

#else

#  define CTD_API static

#endif

/* Global declarations need external linkage in API builds but must remain
** internal alongside CTD_API definitions in production-style builds. */
#if defined(CTD_C_API) || defined(CTD_C_API_DEFAULT)
#  define CTD_DATA_API CTD_API extern
#else
#  define CTD_DATA_API static
#endif

/*----------------------------- API Declaration -----------------------------*/


#ifdef __cplusplus
extern "C" {
#endif

/*
** Constants.
*/
#define LATIN \
  "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
  "abcdefghijklmnopqrstuvwxyz"

/* 
** Recommended canonical pattern catalogue
**   1. Globals and status values.
**   2. Scalar and value operations.
**   3. Scalar pointer operations.
**   4. Typed arrays.
**   5. Byte buffers.
**   6. Strings.
**   7. Structures and tagged unions.
**   8. Opaque handles and release. 
*/

#include "ctd_api.h"

#ifdef __cplusplus
}
#endif

#endif /* CTD_H */
