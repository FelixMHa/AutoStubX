# Define Cython types for explicit type declarations
cdef class BOOL:
    cdef public bint value  # Using bint for boolean values in Cython
    cdef public bint error

    def __init__(self, bint value):
        self.value = value
        self.error = False

    def __repr__(self):
        return f"BOOL({self.value})"


cdef class FLOAT:
    cdef public float value  # Using float for floating-point numbers
    cdef public bint error

    def __init__(self, float value):
        self.value = value
        self.error = False

    def __repr__(self):
        return f"FLOAT({self.value})"


cdef class INT:
    cdef public long value
    cdef public bint error

    def __init__(self, object value):
        self.value = value
        self.error = False

    def __repr__(self):
        return f"INT({self.value})"


cdef class STRING:
    cdef public object value  # In Cython, strings are often handled as char* for C compatibility, but for simplicity, we might keep it as Python object
    cdef public bint error

    def __init__(self, value):
        self.value = value
        self.error = False

    def __repr__(self):
        return f"STRING('{self.value}')"
