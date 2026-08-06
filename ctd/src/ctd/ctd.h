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
** Build modes:
**
**   no defines
**       Production build. CTD symbols have internal linkage.
**
**   CTD_C_API + CTD_BUILD_LIB
**       Build the test shared library and export CTD symbols.
**
**   CTD_C_API + CTD_USE_LIB
**       Consume the test shared library and import CTD symbols.
*/

#if defined(CTD_BUILD_LIB) && defined(CTD_USE_LIB)
#  error "CTD_BUILD_LIB and CTD_USE_LIB are mutually exclusive"
#endif

#if !defined(CTD_C_API) && (defined(CTD_BUILD_LIB) || defined(CTD_USE_LIB))
#  define CTD_API
#endif


#if defined(CTD_C_API)

#  if defined(CTD_BUILD_LIB)

#    if defined(_WIN32)
#      define CTD_API             __declspec(dllexport)
#      define CTD_DATA_DEF        __declspec(dllexport)
#      define CTD_DATA_API extern __declspec(dllexport)
#    elif defined(__GNUC__) || defined(__clang__)
#      define CTD_API             __attribute__((visibility("default")))
#      define CTD_DATA_DEF        __attribute__((visibility("default")))
#      define CTD_DATA_API extern __attribute__((visibility("default")))
#    else
#      define CTD_API
#      define CTD_DATA_DEF
#      define CTD_DATA_API extern
#    endif

#  elif defined(CTD_USE_LIB)

#    if defined(_WIN32)
#      define CTD_API             __declspec(dllimport)
#      define CTD_DATA_API extern __declspec(dllimport)
#    else
#      define CTD_API
#      define CTD_DATA_API extern
#    endif

/*
** A library consumer must not compile CTD data definitions. Define this
** macro only to make accidental use produce an immediate compiler error.
*/
#    define CTD_DATA_DEF CTD_DATA_DEF_IS_NOT_ALLOWED_IN_A_LIBRARY_CONSUMER

#  else
#    error "CTD_C_API requires CTD_BUILD_LIB or CTD_USE_LIB"
#  endif

#elif defined(CTD_STATIC_LIB)

#  define CTD_API
#  define CTD_DATA_API extern
#  define CTD_DATA_DEF

#else

#  define CTD_API      static
#  define CTD_DATA_API static
#  define CTD_DATA_DEF static

#endif /* CTD_C_API */


#ifdef __cplusplus
extern "C" {
#endif

/*
** Constants.
*/
#define CTD_LATIN \
  "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
  "abcdefghijklmnopqrstuvwxyz"

/*
** Canonical API pattern catalogue:
**
**   1. Globals, constants, enums, and status values.
**   2. Scalar value operations.
**   3. Scalar pointer operations.
**   4. Typed arrays.
**   5. Capacity-bounded byte buffers.
**   6. Null-terminated strings.
**   7. Structures and tagged unions.
**   8. Opaque handles, ownership, and release.
**
** Each applicable family includes success, boundary, NULL, failure, and
** capacity-reporting protocols.
*/

#include "ctd_api.h"

#ifdef __cplusplus
}
#endif

#endif /* CTD_H */
