Create a detailed plan to revise and extend the main demo involving the C library sources in `ctd.c`, `ctd.h`, and `ctd_api.h` , as well as the associated `ctd_demo.py` module.

The architectural separation, particularly `ctd.h`, vs `ctd_api.h` must remain the same: typedefs, enums, and prototypes of variables and functions go into `ctd_api.h`, which has dual use as a library component and  CFFI `ffi.cdef()` input.

The objectives and scope of the revision is outlined in the LLM analysis provided below. I want you to use the current code and revise/extend/evolve it according to this analysis.

### Additional requirements

#### Content

- All typedefs, variables, enums, and functions should represent intuitive sensible concepts without unnecessary complexity, e.g., 

```c
typedef enum ctd_status {
    CTD_OK = 0,
    CTD_ERROR_NULL = 1,
    CTD_ERROR_RANGE = 2,
    CTD_ERROR_CAPACITY = 3,
    CTD_ERROR_ALLOCATION = 4,
    CTD_ERROR_DIVIDE_BY_ZERO = 5
} ctd_status;

typedef struct ctd_point {
    double x;
    double y;
} ctd_point;

CTD_API const char ctd_global_name[] = "ctd";
CTD_API const ctd_point ctd_global_origin = {0.0, 0.0};

CTD_API const char *ctd_version(void) {
    return "ctd 1.0";
}

CTD_API const char *ctd_status_name(ctd_status status) {
    switch (status) {
        case CTD_OK:
            return "CTD_OK";
        case CTD_ERROR_NULL:
            return "CTD_ERROR_NULL";
        case CTD_ERROR_RANGE:
            return "CTD_ERROR_RANGE";
        case CTD_ERROR_CAPACITY:
            return "CTD_ERROR_CAPACITY";
        case CTD_ERROR_ALLOCATION:
            return "CTD_ERROR_ALLOCATION";
        case CTD_ERROR_DIVIDE_BY_ZERO:
            return "CTD_ERROR_DIVIDE_BY_ZERO";
        default:
            return "CTD_ERROR_UNKNOWN";
    }
}

CTD_API int ctd_add(int a, int b) {
    return a + b;
}

CTD_API ctd_status ctd_ascii_upper(char *buffer, size_t capacity) {
    size_t index;

    if (buffer == NULL) {
        return CTD_ERROR_NULL;
    }

    for (index = 0; index < capacity; ++index) {
        unsigned char character = (unsigned char)buffer[index];

        if (character == '\0') {
            return CTD_OK;
        }

        if (character >= 'a' && character <= 'z') {
            buffer[index] = (char)(character - 'a' + 'A');
        }
    }

    return CTD_ERROR_CAPACITY;
}

CTD_API ctd_point ctd_point_make(double x, double y) {
    ctd_point result;

    result.x = x;
    result.y = y;

    return result;
}

CTD_API ctd_point ctd_point_add(ctd_point a, ctd_point b) {
    ctd_point result;

    result.x = a.x + b.x;
    result.y = a.y + b.y;

    return result;
}

CTD_API double ctd_point_dot(const ctd_point *a, const ctd_point *b) {
    if (a == NULL || b == NULL) {
        return 0.0;
    }

    return a->x * b->x + a->y * b->y;
}

CTD_API ctd_status ctd_point_translate(ctd_point *point, double dx, double dy) {
    if (point == NULL) {
        return CTD_ERROR_NULL;
    }

    point->x += dx;
    point->y += dy;

    return CTD_OK;
}

CTD_API void ctd_free(void *pointer) {
    free(pointer);
}

CTD_API int ctd_global_counter_increment(void) {
    ctd_global_counter += 1;
    return ctd_global_counter;
}

CTD_API double ctd_hypot_squared(double x, double y) {
    return x * x + y * y;
}
```

- Do not reduce the range of demonstrated interoperation contracts, but remove redundant catalogue entries and use the general CTD release function for allocations that need no special teardown.
- Ideally define a small group of topics suitable for simple and intuitive demonstration of multiple aspects, such as the case of point operation above.
- I want to have
    - 2-3 different enums (with sensible use in the demo functions);
    - 3-5 global variables and 3-5 constants of different types;
    - 5-10 structures of varying complexity.
- Advanced typedefs (I want them to see them in CFFI, but their definitions should probably be clustered in block not meant to be included into few shot examples set for LLM)
    - at least one union;
    - 2-3 typedefs defining function pointers, such as callback;
    - 2-4 typedefs involving opaque pointers and structures;
    - basic self-referential examples (such as defining file system objects or general tree nodes).

#### Organization

Use "### Recommended canonical pattern catalogue" to organize `ctd.c`, `ctd.h`, and `ctd_demo.py`. Include clear comments to attribute patterns and demo code sections.

Make sure the `ctd_demo.py` is well structured rather than having one "main dump". For each pattern, define a dedicated function, that should demonstrate both normal pattern use and patterns for pytest.
