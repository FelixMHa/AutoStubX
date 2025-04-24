import numpy as np
from DummyTypes import FLOAT, STRING, BOOL, INT
import math

def string_length(input1: STRING) -> INT:
    if input1.error:
        dummy = INT(0)
        dummy.error = True
        return dummy

    return INT(len(input1.value))


def string_concat(input1: STRING, input2: STRING) -> STRING:
    if input1.error:
        return input1
    if input2.error:
        return input2

    return STRING(input1.value + input2.value)


def string_contains(input1: STRING, input2: STRING) -> BOOL:
    if input1.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy
    if input2.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy

    return BOOL(input2.value in input1.value)


def string_index_of(input1: STRING, input2: STRING) -> INT:
    if input1.error:
        dummy = INT(0)
        dummy.error = True
        return dummy
    if input2.error:
        dummy = INT(0)
        dummy.error = True
        return dummy

    return INT(input1.value.find(input2.value))


def string_replace(input1: STRING, input2: STRING, input3: STRING) -> STRING:
    if input1.error:
        return input1
    if input2.error:
        return input2
    if input3.error:
        return input3

    # replace the first occurrence of input2 in input1 with input3
    return STRING(input1.value.replace(input2.value, input3.value, 1))


def string_replace_all(input1: STRING, input2: STRING, input3: STRING) -> STRING:
    if input1.error:
        return input1
    if input2.error:
        return input2
    if input3.error:
        return input3

    # replace all occurrences of input2 in input1 with input3
    return STRING(input1.value.replace(input2.value, input3.value))


def string_substring(input1: STRING, input2: INT, input3: INT) -> STRING:
    if input1.error:
        return input1
    if input2.error:
        dummy = STRING('')
        dummy.error = True
        return dummy
    if input3.error:
        dummy = STRING('')
        dummy.error = True
        return dummy

    # make sure input2 is less than input3
    if input2.value > input3.value:
        input1.error = True
        return input1

    # make sure input2 and input3 are positive
    if input2.value < 0 or input3.value < 0:
        input1.error = True
        return input1

    # make sure input2 and input3 are less than the length of input1
    if input2.value > len(input1.value) or input3.value > len(input1.value):
        input1.error = True
        return input1

    return STRING(input1.value[input2.value:input3.value])


def string_to_int(input1: STRING) -> INT:
    if input1.error:
        dummy = INT(0)
        dummy.error = True
        return dummy

    # check if input is a float
    try:
        return INT(int(input1.value))
    except ValueError:
        dummy = INT(0)
        dummy.error = True
        return dummy


def int_to_string(input1: INT) -> STRING:
    if input1.error:
        dummy = STRING('')
        dummy.error = True
        return dummy

    return STRING(str(input1.value))

def string_to_float(input1: STRING) -> FLOAT:
    if input1.error:
        dummy = FLOAT(0)
        dummy.error = True
        return dummy

    # check if input is a float
    try:
        return FLOAT(float(input1.value))
    except ValueError:
        dummy = FLOAT(0)
        dummy.error = True
        return dummy


def float_to_string(input1: FLOAT) -> STRING:
    if input1.error:
        dummy = STRING('')
        dummy.error = True
        return dummy

    return STRING(str(f"{input1.value:.17g}")) # make it as similar as possible to the java float representation


def str_compare(input1: STRING, input2: STRING) -> BOOL:
    if input1.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy
    if input2.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy

    return BOOL(input1.value == input2.value)


def str_if_then_else(input1: BOOL, input2: STRING, input3: STRING) -> STRING:
    if input1.error:
        dummy = STRING('')
        dummy.error = True
        return dummy
    if input2.error:
        return input2
    if input3.error:
        return input3

    if input1.value:
        return input2

    return input3


def ascii_to_string(input1: INT) -> STRING:  # Int -> String
    if input1.error:
        dummy = STRING('')
        dummy.error = True
        return dummy

    # check if input is in the range of ascii characters
    if input1.value < 0 or input1.value > 255:
        dummy = STRING('')
        dummy.error = True
        return dummy

    return STRING(chr(input1.value))


def string_to_ascii(input1: STRING) -> INT:  # String -> Int
    if input1.error:
        dummy = INT(0)
        dummy.error = True
        return dummy

    # make sure length of input1 is => 1
    if len(input1.value) != 1:
        dummy = INT(0)
        dummy.error = True
        return dummy

    c = input1.value[0]

    # check if input is a float
    try:
        return INT(ord(c))
    except ValueError:
        dummy = INT(0)
        dummy.error = True
        return dummy


def real_neg(input1: FLOAT) -> FLOAT:
    if input1.error:
        return input1

    return FLOAT(input1.value * -1)


def real_add(input1: FLOAT, input2: FLOAT) -> FLOAT:
    if input1.error:
        return input1
    if input2.error:
        return input2

    return FLOAT(input1.value + input2.value)


def real_sub(input1: FLOAT, input2: FLOAT) -> FLOAT:
    if input1.error:
        return input1
    if input2.error:
        return input2

    return FLOAT(input1.value - input2.value)


def real_div(input1: FLOAT, input2: FLOAT) -> FLOAT:
    if input1.error:
        return input1
    if input2.error:
        return input2

    # check if input2 is 0
    if input2.value == 0:
        dummy = FLOAT(0)
        dummy.error = True
        return dummy

    return FLOAT(input1.value / input2.value)

def real_cos(input1: FLOAT) -> FLOAT:
    if input1.error:
        return input1

    return FLOAT(float(np.cos(input1.value)))

def real_mul(input1: FLOAT, input2: FLOAT) -> FLOAT:
    if input1.error:
        return input1
    if input2.error:
        return input2

    return FLOAT(input1.value * input2.value)


def real_floor(input1: FLOAT) -> FLOAT:
    if input1.error:
        return input1

    return FLOAT(np.floor(input1.value))


def real_abs(input1: FLOAT) -> FLOAT:
    if input1.error:
        return input1

    return FLOAT(abs(input1.value))


def real_if_then_else(input1: BOOL, input2: FLOAT, input3: FLOAT) -> FLOAT:
    if input1.error:
        dummy = FLOAT(0)
        dummy.error = True
        return dummy
    if input2.error:
        return input2
    if input3.error:
        return input3

    if input1:
        return input2

    return input3


def real_less_than(input1: FLOAT, input2: FLOAT) -> BOOL:
    if input1.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy
    if input2.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy

    return BOOL(input1.value < input2.value)


def real_compare_as_int(input1: FLOAT, input2: FLOAT) -> BOOL:
    if input1.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy
    if input2.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy

    return BOOL(int(input1.value) == int(input2.value))


def logic_not(input1: BOOL) -> BOOL:
    if input1.error:
        return input1

    return BOOL(not input1.value)


def logic_and(input1: BOOL, input2: BOOL) -> BOOL:
    if input1.error:
        return input1
    if input2.error:
        return input2

    return BOOL(input1.value and input2.value)


def logic_or(input1: BOOL, input2: BOOL) -> BOOL:
    if input1.error:
        return input1
    if input2.error:
        return input2

    return BOOL(input1.value or input2.value)


def logic_xor(input1: BOOL, input2: BOOL) -> BOOL:
    if input1.error:
        return input1
    if input2.error:
        return input2

    return BOOL(input1.value ^ input2.value)


def int_neg(input1: INT) -> INT:
    if input1.error:
        return input1

    return INT(input1.value * -1)


def int_add(input1: INT, input2: INT) -> INT:
    if input1.error:
        return input1

    return INT(input1.value + input2.value)


def int_sub(input1: INT, input2: INT) -> INT:
    if input1.error:
        return input1

    return INT(input1.value - input2.value)


def int_div(input1: INT, input2: INT) -> FLOAT:
    if input1.error:
        return input1
    if input2.error:
        return input2

    # check if input2 is 0
    if input2.value == 0:
        dummy = INT(0)
        dummy.error = True
        return dummy

    return FLOAT(input1.value / input2.value)


def int_mul(input1: INT, input2: INT) -> INT:
    if input1.error:
        return input1
    if input2.error:
        return input2

    return INT(input1.value * input2.value)

def int_abs(input1: INT) -> INT:
    if input1.error:
        return input1

    if input1.value < 0:
        return INT(-input1.value)

    return input1


def int_if_then_else(input1: BOOL, input2: INT, input3: INT) -> INT:
    if input1.error:
        dummy = INT(0)
        dummy.error = True
        return dummy
    if input2.error:
        return input2
    if input3.error:
        return input3

    if input1:
        return input2

    return input3


def int_less_than(input1: INT, input2: INT) -> BOOL:
    if input1.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy
    if input2.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy

    return BOOL(input1.value < input2.value)


def int_compare(input1: INT, input2: INT) -> BOOL:
    if input1.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy
    if input2.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy

    return BOOL(input1.value == input2.value)


def int_compare_range(input1: INT, input2: INT, input3: INT) -> BOOL:
    if input1.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy
    if input2.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy
    if input3.error:
        dummy = BOOL(False)
        dummy.error = True
        return dummy

    return BOOL(input2.value <= input1.value and input1.value <= input3.value)
