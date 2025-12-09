#!/usr/bin/env python3
"""
PushGP Implementation for Data Structure Method Learning

This fixes the issues from the initial implementation and provides a more
robust PushGP system specifically designed for learning Java method approximations.
"""

import random
import copy
import os
from itertools import zip_longest
import math
import difflib
from collections import defaultdict
from typing import Dict, List, Any, Union, Optional
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
try:
    import Levenshtein
    _levenshtein = lambda a, b: Levenshtein.distance(a, b)
except Exception:
    _levenshtein = None

GLOBAL_TRAINING_DATA = None
GLOBAL_INTERPRETER = None
EPS = 1e-9
def init_worker(training_data, interpreter):
    """Initialize worker process with shared data"""
    global GLOBAL_TRAINING_DATA, GLOBAL_INTERPRETER
    GLOBAL_TRAINING_DATA = training_data
    GLOBAL_INTERPRETER = interpreter   

@dataclass
class TrainingExample:
    """Training example with method sequence and expected output"""
    sequence: List[str]
    input_args: List[List[Any]]
    expected_outputs: List[Any]
    type_inputs: List[List[str]]
    type_outputs: List[str]
    data_structure_type: str

class PushState:
    """ Push state with better argument handling"""
    
    def __init__(self, max_steps: int = 150):
        # Core Push stacks
        self.integer_stack = []
        self.boolean_stack = []
        self.string_stack = []
        self.float_stack = []
        self.exec_stack = []
        self.error_stack = []
        # Domain-specific stacks
        self.data_structure_stack = []
        self.result = None

        
        # HashMap/Map storage
        self.map_storage = {}  # For key-value pairs
        
        # Execution state
        self.step_count = 0
        self.max_steps = max_steps  # Cap per-program steps to bound evaluation time
        
    def copy(self):
        """Deep copy of state"""
        new_state = PushState(max_steps=self.max_steps)
        new_state.integer_stack = self.integer_stack.copy()
        new_state.boolean_stack = self.boolean_stack.copy()
        new_state.string_stack = self.string_stack.copy()
        new_state.float_stack = self.float_stack.copy()
        new_state.exec_stack = copy.deepcopy(self.exec_stack)
        new_state.data_structure_stack = copy.deepcopy(self.data_structure_stack)
        new_state.result = self.result
        new_state.map_storage = self.map_storage.copy()
        new_state.step_count = self.step_count
        new_state.max_steps = self.max_steps
        return new_state
    
     
    def pop_from_any_stack(self):
        if self.string_stack:
            return self.string_stack.pop()
        elif self.integer_stack:
            return self.integer_stack.pop()
        elif self.boolean_stack:
            return self.boolean_stack.pop()
        elif self.float_stack:
            return self.float_stack.pop()
        return None
    
    def push_to_appropriate_stack(self, value):
        """Push value to appropriate typed stack"""
        if isinstance(value, bool):
            self.boolean_stack.append(value)
        elif isinstance(value, int):
            self.integer_stack.append(value)
        elif isinstance(value, str):
            self.string_stack.append(value)
        elif isinstance(value, float):
            self.float_stack.append(value)

    def to_dict(self):
        return {
            "integer_stack": self.integer_stack.copy(),
            "boolean_stack": self.boolean_stack.copy(),
            "string_stack": self.string_stack.copy(),
            "float_stack": self.float_stack.copy(),
            "data_structure_stack": copy.deepcopy(self.data_structure_stack),
            "result": self.result,
            "step_count": self.step_count,
        }

class PushInstruction:
    """Base class for  Push instructions"""
    
    def __init__(self, name: str):
        self.name = name
    
    def execute(self, state: PushState):
        """Execute instruction on state"""
        raise NotImplementedError
    
    def __repr__(self):
        return self.name
    
    def __eq__(self, other):
        return isinstance(other, PushInstruction) and self.name == other.name
    
    def __hash__(self):
        return hash(self.name)

#  Core Push Instructions
#Integer Instructions
class INT_CONST(PushInstruction):
    def __init__(self, value: int):
        super().__init__(f"INT.CONST.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.integer_stack.append(self.value)


class INT_ADD(PushInstruction):
    def __init__(self):
        super().__init__("INT.ADD")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a + b)


class INT_SUB(PushInstruction):
    def __init__(self):
        super().__init__("INT.SUB")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a - b)


class INT_MUL(PushInstruction):
    def __init__(self):
        super().__init__("INT.MUL")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a * b)


class INT_DIV(PushInstruction):
    def __init__(self):
        super().__init__("INT.DIV")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            if b != 0:
                state.integer_stack.append(a // b)


class INT_MOD(PushInstruction):
    def __init__(self):
        super().__init__("INT.MOD")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            if b != 0:
                state.integer_stack.append(a % b)
            else:
                state.integer_stack.append(a)


class INT_NEG(PushInstruction):
    def __init__(self):
        super().__init__("INT.NEG")

    def execute(self, state: PushState):
        if state.integer_stack:
            state.integer_stack.append(-state.integer_stack.pop())


class INT_LT(PushInstruction):
    def __init__(self):
        super().__init__("INT.LT")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.boolean_stack.append(a < b)


class INT_GT(PushInstruction):
    def __init__(self):
        super().__init__("INT.GT")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.boolean_stack.append(a > b)


class INT_EQ(PushInstruction):
    def __init__(self):
        super().__init__("INT.EQ")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.boolean_stack.append(a == b)

class INT_ABS(PushInstruction):
    def __init__(self):
        super().__init__("INT.ABS")

    def execute(self, state: PushState):
        if state.integer_stack:
            _int=state.integer_stack.pop()
            if _int<0:
                state.integer_stack.append(-_int)
            else:
                state.integer_stack.append(_int)


class INT_COMPARE_RANGE(PushInstruction):
    def __init__(self):
        super().__init__("INT.COMPARE_RANGE")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 3:
            upper = state.integer_stack.pop()
            lower = state.integer_stack.pop()
            value = state.integer_stack.pop()
            state.boolean_stack.append(lower <= value <= upper)

class ITE_INT(PushInstruction):
    def __init__(self):
        super().__init__("INT.ITE")

    def execute(self, state: PushState):
        if state.boolean_stack and len(state.integer_stack) >= 2:
            false_val = state.integer_stack.pop()
            true_val = state.integer_stack.pop()
            cond = state.boolean_stack.pop()
            state.integer_stack.append(true_val if cond else false_val)



# Float instructions
class FLOAT_CONST(PushInstruction):
    def __init__(self, value: float):
        super().__init__(f"FLOAT.CONST.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.float_stack.append(self.value)


class FLOAT_ADD(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.ADD")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.float_stack.append(a + b)


class FLOAT_SUB(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.SUB")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.float_stack.append(a - b)


class FLOAT_MUL(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.MUL")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.float_stack.append(a * b)


class FLOAT_DIV(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.DIV")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            if b != 0.0:
                state.float_stack.append(a / b)


class FLOAT_NEG(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.NEG")

    def execute(self, state: PushState):
        if state.float_stack:
            state.float_stack.append(-state.float_stack.pop())


class FLOAT_ABS(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.ABS")

    def execute(self, state: PushState):
        if state.float_stack:
            state.float_stack.append(abs(state.float_stack.pop()))


class FLOAT_FLOOR(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.FLOOR")

    def execute(self, state: PushState):
        if state.float_stack:
            state.float_stack.append(math.floor(state.float_stack.pop()))


class FLOAT_COS(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.COS")

    def execute(self, state: PushState):
        if state.float_stack:
            state.float_stack.append(math.cos(state.float_stack.pop()))


class FLOAT_LT(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.LT")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.boolean_stack.append(a < b)


class FLOAT_GT(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.GT")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.boolean_stack.append(a > b)


class FLOAT_EQ(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.EQ")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.boolean_stack.append(a == b)


class FLOAT_IS_NAN(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.IS_NAN")

    def execute(self, state: PushState):
        if state.float_stack:
            state.boolean_stack.append(math.isnan(state.float_stack.pop()))


class FLOAT_IS_INF(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.IS_INF")

    def execute(self, state: PushState):
        if state.float_stack:
            state.boolean_stack.append(math.isinf(state.float_stack.pop()))


class FLOAT_IS_FINITE(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.IS_FINITE")

    def execute(self, state: PushState):
        if state.float_stack:
            state.boolean_stack.append(math.isfinite(state.float_stack.pop()))


class FLOAT_TO_STR(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.TO.STR")

    def execute(self, state: PushState):
        if state.float_stack:
            value = state.float_stack.pop()
            state.string_stack.append(str(value))


class STR_TO_FLOAT(PushInstruction):
    def __init__(self):
        super().__init__("STR.TO.FLOAT")

    def execute(self, state: PushState):
        if state.string_stack:
            s = state.string_stack.pop()
            try:
                state.float_stack.append(float(s))
            except Exception:
                state.string_stack.append("error")

class ITE_FLOAT(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.ITE")

    def execute(self, state: PushState):
        if state.boolean_stack and len(state.float_stack) >= 2:
            false_val = state.float_stack.pop()
            true_val = state.float_stack.pop()
            cond = state.boolean_stack.pop()
            state.float_stack.append(true_val if cond else false_val)

#ERCs
class ERC_INT(PushInstruction):
    def __init__(self, value: int = None):
        if value is None:
            value = int(random.uniform(-10, 256))
        super().__init__(f"ERC.INT.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.integer_stack.append(self.value)
        
class ERC_FLOAT(PushInstruction):
    def __init__(self, value: int = None):
        if value is None:
            if random.random() < 0.5:
                value = float(random.uniform(-256, 256))
            else:
                value = float(random.uniform(-1, 1))
        super().__init__(f"ERC.FLOAT.{value:.2f}")
        self.value = value

    def execute(self, state: PushState):
        state.float_stack.append(self.value)

#Boolean Instructions
class BOOL_CONST(PushInstruction):
    def __init__(self, value: bool):
        super().__init__(f"BOOL.CONST.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.boolean_stack.append(self.value)


class BOOL_AND(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.AND")

    def execute(self, state: PushState):
        if len(state.boolean_stack) >= 2:
            b = state.boolean_stack.pop()
            a = state.boolean_stack.pop()
            state.boolean_stack.append(a and b)


class BOOL_OR(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.OR")

    def execute(self, state: PushState):
        if len(state.boolean_stack) >= 2:
            b = state.boolean_stack.pop()
            a = state.boolean_stack.pop()
            state.boolean_stack.append(a or b)


class BOOL_XOR(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.XOR")

    def execute(self, state: PushState):
        if len(state.boolean_stack) >= 2:
            b = state.boolean_stack.pop()
            a = state.boolean_stack.pop()
            state.boolean_stack.append(a ^ b)


class BOOL_NOT(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.NOT")

    def execute(self, state: PushState):
        if state.boolean_stack:
            state.boolean_stack.append(not state.boolean_stack.pop())


class BOOL_TO_INT(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.TO.INT")

    def execute(self, state: PushState):
        if state.boolean_stack:
            state.integer_stack.append(1 if state.boolean_stack.pop() else 0)


class ITE_BOOL(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.ITE")

    def execute(self, state: PushState):
        if state.boolean_stack and len(state.boolean_stack) >= 2:
            false_val = state.boolean_stack.pop()
            true_val = state.boolean_stack.pop()
            cond = state.boolean_stack.pop()
            state.boolean_stack.append(true_val if cond else false_val)

#BIT 
class BIT_AND(PushInstruction):
    def __init__(self):
        super().__init__("BIT.AND")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a & b)


class BIT_OR(PushInstruction):
    def __init__(self):
        super().__init__("BIT.OR")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a | b)


class BIT_XOR(PushInstruction):
    def __init__(self):
        super().__init__("BIT.XOR")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a ^ b)


class BIT_NOT(PushInstruction):
    def __init__(self):
        super().__init__("BIT.NOT")

    def execute(self, state: PushState):
        if state.integer_stack:
            a = state.integer_stack.pop()
            state.integer_stack.append(~a)


class BIT_SHL(PushInstruction):
    def __init__(self):
        super().__init__("BIT.SHL")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            shift = state.integer_stack.pop()
            value = state.integer_stack.pop()
            state.integer_stack.append(value << shift)


class BIT_SHR(PushInstruction):
    def __init__(self):
        super().__init__("BIT.SHR")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            shift = state.integer_stack.pop()
            value = state.integer_stack.pop()
            state.integer_stack.append(value >> shift)


#String Instructions

# String Instructions (renamed to match your desired naming)
class STR_CONCAT(PushInstruction):
    def __init__(self):
        super().__init__("STR_CONCAT")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2:
            b = state.string_stack.pop()
            a = state.string_stack.pop()
            state.string_stack.append(a + b)


class STR_EQ(PushInstruction):
    def __init__(self):
        super().__init__("STR_EQ")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2:
            b = state.string_stack.pop()
            a = state.string_stack.pop()
            state.boolean_stack.append(a == b)


class STR_LEN(PushInstruction):
    def __init__(self):
        super().__init__("STR_LEN")

    def execute(self, state: PushState):
        if state.string_stack:
            state.integer_stack.append(len(state.string_stack.pop()))


class STR_CHAR_AT(PushInstruction):
    def __init__(self):
        super().__init__("STR_CHAR_AT")

    def execute(self, state: PushState):
        if state.string_stack and state.integer_stack:
            index = state.integer_stack.pop()
            s = state.string_stack.pop()
            if 0 <= index < len(s):
                state.string_stack.append(s[index])


class STR_STARTS_WITH(PushInstruction):
    def __init__(self):
        super().__init__("STR_STARTS_WITH")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2:
            prefix = state.string_stack.pop()
            s = state.string_stack.pop()
            state.boolean_stack.append(s.startswith(prefix))


class STR_CONTAINS(PushInstruction):
    def __init__(self):
        super().__init__("STR_CONTAINS")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2:
            sub = state.string_stack.pop()
            s = state.string_stack.pop()
            state.boolean_stack.append(sub in s)


class STR_INDEX_OF(PushInstruction):
    def __init__(self):
        super().__init__("STR_INDEX_OF")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2 and state.integer_stack:
            start = state.integer_stack.pop()
            sub = state.string_stack.pop()
            s = state.string_stack.pop()
            state.integer_stack.append(s.find(sub, max(0, start)))


class STR_SUBSTRING(PushInstruction):
    def __init__(self):
        super().__init__("STR_SUBSTRING")

    def execute(self, state: PushState):
        if state.string_stack and len(state.integer_stack) >= 2:
            end = state.integer_stack.pop()
            start = state.integer_stack.pop()
            s = state.string_stack.pop()
            state.string_stack.append(s[start:end] if 0 <= start <= end <= len(s) else "")


class STR_REPLACE(PushInstruction):
    def __init__(self):
        super().__init__("STR_REPLACE")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 3:
            new = state.string_stack.pop()
            old = state.string_stack.pop()
            s = state.string_stack.pop()
            state.string_stack.append(s.replace(old, new))


class STR_REPLACE_ALL(PushInstruction):
    def __init__(self):
        super().__init__("STR_REPLACE_ALL")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 3:
            new = state.string_stack.pop()
            old = state.string_stack.pop()
            s = state.string_stack.pop()
            state.string_stack.append(s.replace(old, new))


class STR_TO_INT(PushInstruction):
    def __init__(self):
        super().__init__("STR_TO_INT")

    def execute(self, state: PushState):
        if state.string_stack:
            s = state.string_stack.pop()
            try:
                state.integer_stack.append(int(s))
            except:
                state.integer_stack.append(0)


class INT_TO_STR(PushInstruction):
    def __init__(self):
        super().__init__("INT_TO_STR")

    def execute(self, state: PushState):
        if state.integer_stack:
            state.string_stack.append(str(state.integer_stack.pop()))


class ASCII_TO_STR(PushInstruction):
    def __init__(self):
        super().__init__("ASCII_TO_STR")

    def execute(self, state: PushState):
        if state.integer_stack:
            code = state.integer_stack.pop()
            try:
                state.string_stack.append(chr(max(0, int(code)) % 1114112))
            except:
                state.string_stack.append("")


class STR_TO_ASCII(PushInstruction):
    def __init__(self):
        super().__init__("STR_TO_ASCII")

    def execute(self, state: PushState):
        if state.string_stack:
            s = state.string_stack.pop()
            state.integer_stack.append(ord(s[0]) if s else -1)


class STR_TO_LOWER(PushInstruction):
    def __init__(self):
        super().__init__("STR_TO_LOWER")

    def execute(self, state: PushState):
        if state.string_stack:
            state.string_stack.append(state.string_stack.pop().lower())


class STR_TO_UPPER(PushInstruction):
    def __init__(self):
        super().__init__("STR_TO_UPPER")

    def execute(self, state: PushState):
        if state.string_stack:
            state.string_stack.append(state.string_stack.pop().upper())


class STR_TRIM(PushInstruction):
    def __init__(self):
        super().__init__("STR_TRIM")

    def execute(self, state: PushState):
        if state.string_stack:
            state.string_stack.append(state.string_stack.pop().strip())


class STR_ITE(PushInstruction):
    def __init__(self):
        super().__init__("STR_ITE")

    def execute(self, state: PushState):
        if state.boolean_stack and len(state.string_stack) >= 2:
            false_val = state.string_stack.pop()
            true_val = state.string_stack.pop()
            cond = state.boolean_stack.pop()
            state.string_stack.append(true_val if cond else false_val)

class STR_CONST(PushInstruction):
    def __init__(self, value: str):
        super().__init__(f"STR.CONST.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.string_stack.append(self.value)

#  Execution Control
class EXEC_IF(PushInstruction):
    def __init__(self):
        super().__init__("EXEC.IF")

    def execute(self, state: PushState):
        # Expect a boolean on the stack and two code blocks (true/false branches)
        if state.boolean_stack and len(state.exec_stack) >= 2:
            condition = state.boolean_stack.pop()
            false_branch = state.exec_stack.pop()
            true_branch = state.exec_stack.pop()
            if condition:
                state.exec_stack.append(true_branch)
            else:
                state.exec_stack.append(false_branch)


class EXEC_DO_TIMES(PushInstruction):
    def __init__(self):
        super().__init__("EXEC.DO_TIMES")

    def execute(self, state: PushState):
        # Expect integer count and one code block
        if state.integer_stack and state.exec_stack:
            count = state.integer_stack.pop()
            block = state.exec_stack.pop()
            for _ in range(max(0, count)):
                state.exec_stack.append(block)

#Utility Instructions
class DUP_ANY(PushInstruction):
    def __init__(self, arg_index: int = 0):
        super().__init__("DUP.ANY")
    
    def execute(self, state: PushState):
        if state.integer_stack:
            state.integer_stack.append(state.integer_stack[-1])
        if state.boolean_stack:
            state.boolean_stack.append(state.boolean_stack[-1])
        if state.string_stack:
            state.string_stack.append(state.string_stack[-1])
        if state.float_stack:
            state.float_stack.append(state.float_stack[-1])

class SWAP_ANY(PushInstruction):
    def __init__(self):
        super().__init__("SWAP.ANY")

    def execute(self, state: PushState):
        # Swap top two values from the same stack if possible
        for stack in [state.string_stack, state.integer_stack,
                      state.boolean_stack, state.float_stack]:
            if len(stack) >= 2:
                stack[-1], stack[-2] = stack[-2], stack[-1]
                return


class POP_ANY(PushInstruction):
    def __init__(self):
        super().__init__("POP.ANY")

    def execute(self, state: PushState):
        # Remove top element from any stack
        for stack in [state.string_stack, state.integer_stack,
                      state.boolean_stack, state.float_stack]:
            if stack:
                stack.pop()
                return

#  Data Structure Instructions

class DS_SIZE(PushInstruction):
    def __init__(self):
        super().__init__("DS.SIZE")

    def execute(self, state: PushState):
        size = len(state.data_structure_stack)
        state.integer_stack.append(size)


class DS_IS_EMPTY(PushInstruction):
    def __init__(self):
        super().__init__("DS.IS_EMPTY")

    def execute(self, state: PushState):
        is_empty = len(state.data_structure_stack) == 0
        state.boolean_stack.append(is_empty)


class DS_CLEAR(PushInstruction):
    def __init__(self):
        super().__init__("DS.CLEAR")

    def execute(self, state: PushState):
        state.data_structure_stack.clear()


class DS_GET_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.GET.INDEX")

    def execute(self, state: PushState):
        if state.integer_stack:
            index = state.integer_stack.pop()
            if 0 <= index < len(state.data_structure_stack):
                element = state.data_structure_stack[index]
                state.push_to_appropriate_stack(element)
            else:
                state.error_stack.append("error")



class DS_SET_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.SET.INDEX")

    def execute(self, state: PushState):
        if state.integer_stack:
            index = state.integer_stack.pop()
            value = state.pop_from_any_stack()
            if value is not None and 0 <= index < len(state.data_structure_stack):
                old = state.data_structure_stack[index]
                state.data_structure_stack[index] = value
                # Return old value like Java List.set
                state.push_to_appropriate_stack(old)
            else:
                state.error_stack.append("error")


class DS_INSERT_AT_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.INSERT.AT.INDEX")

    def execute(self, state: PushState):
        if state.integer_stack:
            index = state.integer_stack.pop()
            value = state.pop_from_any_stack()
            if value is not None:
                # Allow insert at end like Java add(index, element)
                if 0 <= index <= len(state.data_structure_stack):
                    state.data_structure_stack.insert(index, value)
                    # Return True to mimic add semantics where applicable
                    state.boolean_stack.append(True)
                else:
                    state.error_stack.append("error")



class DS_REMOVE_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.REMOVE.INDEX")

    def execute(self, state: PushState):
        if state.integer_stack:
            index = state.integer_stack.pop()
            if 0 <= index < len(state.data_structure_stack):
                element = state.data_structure_stack.pop(index)
                state.push_to_appropriate_stack(element)
            else:
                state.error_stack.append("error")



class DS_PEEK_LAST(PushInstruction):
    def __init__(self):
        super().__init__("DS.PEEK.LAST")

    def execute(self, state: PushState):
        if state.data_structure_stack:
            element = state.data_structure_stack[-1]
            state.push_to_appropriate_stack(element)
        else:
            state.error_stack.append("error")



class DS_POP_LAST(PushInstruction):
    def __init__(self):
        super().__init__("DS.POP.LAST")

    def execute(self, state: PushState):
        if state.data_structure_stack:
            element = state.data_structure_stack.pop()
            state.push_to_appropriate_stack(element)
        else:
            state.error_stack.append("error")


class DS_LAST_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.LAST.INDEX")

    def execute(self, state: PushState):
        if state.data_structure_stack:
            state.integer_stack.append(len(state.data_structure_stack) - 1)
        else:
            state.integer_stack.append(-1)


class DS_FIRST_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.FIRST.INDEX")

    def execute(self, state: PushState):
        if state.data_structure_stack:
            state.integer_stack.append(0)
        else:
            state.integer_stack.append(-1)


class DS_INDEX_OF(PushInstruction):
    def __init__(self):
        super().__init__("DS.INDEX_OF")

    def execute(self, state: PushState):
        value = state.pop_from_any_stack()
        if value is not None:
            try:
                index = state.data_structure_stack.index(value)
                state.integer_stack.append(index)
            except ValueError:
                # Not found
                state.integer_stack.append(-1)
        else:
            state.error_stack.append("error")


class DS_LAST_INDEX_OF(PushInstruction):
    def __init__(self):
        super().__init__("DS.LAST_INDEX_OF")

    def execute(self, state: PushState):
        value = state.pop_from_any_stack()
        if value is not None:
            try:
                # Reverse search: find last occurrence
                index = len(state.data_structure_stack) - 1 - state.data_structure_stack[::-1].index(value)
                state.integer_stack.append(index)
            except ValueError:
                # Not found
                state.integer_stack.append(-1)
        else:
            state.error_stack.append("error")


class DS_CONTAINS(PushInstruction):
    def __init__(self):
        super().__init__("DS.CONTAINS")

    def execute(self, state: PushState):
        value = state.pop_from_any_stack()
        if value is not None:
            contains = value in state.data_structure_stack
            state.boolean_stack.append(contains)

# HashMap/Map Instructions
class MAP_SIZE(PushInstruction):
    def __init__(self):
        super().__init__("MAP.SIZE")

    def execute(self, state: PushState):
        size = len(state.map_storage)
        state.integer_stack.append(size)


class MAP_IS_EMPTY(PushInstruction):
    def __init__(self):
        super().__init__("MAP.IS_EMPTY")

    def execute(self, state: PushState):
        is_empty = len(state.map_storage) == 0
        state.boolean_stack.append(is_empty)


class MAP_CLEAR(PushInstruction):
    def __init__(self):
        super().__init__("MAP.CLEAR")

    def execute(self, state: PushState):
        state.map_storage.clear()


class MAP_PUT(PushInstruction):
    def __init__(self):
        super().__init__("MAP.PUT")

    def execute(self, state: PushState):
        # Pop key and value from typed stacks
        key = state.pop_from_any_stack()
        value = state.pop_from_any_stack()
        if key is not None and value is not None:
            state.map_storage[key] = value


class MAP_GET(PushInstruction):
    def __init__(self):
        super().__init__("MAP.GET")

    def execute(self, state: PushState):
        key = state.pop_from_any_stack()
        if key is not None and key in state.map_storage:
            value = state.map_storage[key]
            state.push_to_appropriate_stack(value)


class MAP_REMOVE(PushInstruction):
    def __init__(self):
        super().__init__("MAP.REMOVE")

    def execute(self, state: PushState):
        key = state.pop_from_any_stack()
        if key is not None and key in state.map_storage:
            value = state.map_storage.pop(key)
            state.push_to_appropriate_stack(value)


class MAP_CONTAINS_KEY(PushInstruction):
    def __init__(self):
        super().__init__("MAP.CONTAINS_KEY")

    def execute(self, state: PushState):
        key = state.pop_from_any_stack()
        if key is not None:
            state.boolean_stack.append(key in state.map_storage)


class MAP_CONTAINS_VALUE(PushInstruction):
    def __init__(self):
        super().__init__("MAP.CONTAINS_VALUE")

    def execute(self, state: PushState):
        value = state.pop_from_any_stack()
        if value is not None:
            state.boolean_stack.append(value in state.map_storage.values())


class MAP_KEY_SET(PushInstruction):
    def __init__(self):
        super().__init__("MAP.KEY_SET")

    def execute(self, state: PushState):
        keys = list(state.map_storage.keys())
        state.push_to_appropriate_stack(keys)


class MAP_VALUES(PushInstruction):
    def __init__(self):
        super().__init__("MAP.VALUES")

    def execute(self, state: PushState):
        values = list(state.map_storage.values())
        state.push_to_appropriate_stack(values)
            

def create__pushgp_instruction_set(profile: str = 'primitives_full'):
    """Create PushGP instruction set by profile.

    Profiles:
    - 'ds_smt_minimal': minimal, SMT-friendly set for data-structure stubs.
    - 'primitives_full': integer/float/boolean/string primitives for symbolic regression.
    """
    profile = (profile or 'primitives_full').lower()

    if profile == 'ds_smt_minimal':
        instructions = []
        # Integers (linear ops and comparisons only)
        instructions.extend([
            INT_ADD(),
            INT_SUB(),
            INT_EQ(),
            INT_LT(),
        ])
        for i in range(-1, 2):
            instructions.append(INT_CONST(i))
        # Booleans
        instructions.extend([
            BOOL_AND(), BOOL_OR(), BOOL_NOT(),
            BOOL_CONST(True), BOOL_CONST(False),
        ])
        # Utility
        instructions.extend([DUP_ANY(), POP_ANY()])
        # Data structure operations
        instructions.extend([
            DS_SIZE(), DS_CLEAR(),
            DS_GET_INDEX(), DS_SET_INDEX(),
            DS_INSERT_AT_INDEX(), DS_REMOVE_INDEX(),
            DS_INDEX_OF(), DS_LAST_INDEX_OF(),
        ])
        return {instr.name: instr for instr in instructions}

    # Default: primitives_full
    instructions = []

    # Core integers (include linear + multiplicative ops for regression)
    instructions.extend([
        INT_ADD(), INT_SUB(), INT_MUL(), INT_DIV(),
        INT_EQ(), INT_LT(),
        INT_NEG(), INT_ABS(), ITE_INT(),
        INT_COMPARE_RANGE(),
    ])
    for i in range(-4, 7):
        instructions.append(INT_CONST(i))

    # Floats
    instructions.extend([
        FLOAT_ADD(), FLOAT_SUB(), FLOAT_MUL(), FLOAT_DIV(),
        FLOAT_NEG(), FLOAT_ABS(), FLOAT_FLOOR(),
        FLOAT_COS(), FLOAT_LT(), FLOAT_EQ(), ITE_FLOAT(),
        FLOAT_TO_STR(), STR_TO_FLOAT(),
        #FLOAT_IS_NAN(), FLOAT_IS_INF(),
        #FLOAT_IS_FINITE(),
    ])
    for f in [0.0, 1.0, -1.0]:
        instructions.append(FLOAT_CONST(f))

    # Booleans
    instructions.extend([
        BOOL_AND(), BOOL_OR(), BOOL_NOT(), BOOL_XOR(),
        #BOOL_TO_INT(), ITE_BOOL(),
    ])

    instructions.extend([
        BOOL_CONST(True), BOOL_CONST(False),
    ])


    # Strings (minimal core)
    instructions.extend([
        STR_CONCAT(), STR_EQ(), STR_LEN(), STR_CONTAINS(), 
        STR_INDEX_OF(), STR_SUBSTRING(), STR_REPLACE(), STR_REPLACE_ALL(),
        STR_TO_INT(), INT_TO_STR(), ASCII_TO_STR(), STR_TO_ASCII(), STR_ITE(),         
    ])

    instructions.extend([
        STR_CONST(""), STR_CONST(" "),
    ])

    # ERCS
    instructions.extend([
        ERC_INT(),
        ERC_FLOAT()
        ])

    # Utilities helpful for expression building
    instructions.extend([DUP_ANY(), SWAP_ANY(), POP_ANY()])

    return {instr.name: instr for instr in instructions}


class PushProgram:
    """ Push program with better execution"""
    
    def __init__(self, code: List[Union[PushInstruction, List]] = None):
        self.code = code or []
    
    def execute(self, state: PushState):
        """Execute program with  argument handling"""
        # Initialize execution stack with program
        if self.code:
            for instruction in reversed(self.code):
                state.exec_stack.append(instruction)
        
        # Execute until exec stack is empty or max steps reached
        while state.exec_stack and state.step_count < state.max_steps:
            try:
                instruction = state.exec_stack.pop()
                
                if isinstance(instruction, PushInstruction):
                    instruction.execute(state)
                elif isinstance(instruction, list):
                    # Code block - push onto exec stack in reverse order
                    for instr in reversed(instruction):
                        state.exec_stack.append(instr)
                
                state.step_count += 1
            except Exception:
                # Suppress instruction errors during GP evaluation to avoid noise
                continue
        
        return state

class PushGPGenome:
    """ genome with better complexity calculation"""
    
    def __init__(self):
        self.methods: Dict[str, PushProgram] = {}
        self.fitness = float('inf')
        self.accuracy = 0.0
        self.method_accuracies: Dict[str, float] = {}
        self.complexity_penalty = 0.0
    
    def add_method(self, method_name: str, program: PushProgram):
        """Add method program to genome"""
        self.methods[method_name] = program
    
    def get_complexity_penalty(self) -> float:
        """Calculate complexity penalty"""
        total_complexity = 0
        for program in self.methods.values():
            total_complexity += self._count_instructions(program.code)
        return total_complexity * 0.0002
    
    def _count_instructions(self, code: List) -> int:
        """Recursively count instructions"""
        count = 0
        for item in code:
            if isinstance(item, list):
                count += self._count_instructions(item)
            else:
                count += 1
        return count
    
    def copy(self):
        """Deep copy genome"""
        new_genome = PushGPGenome()
        for method_name, program in self.methods.items():
            new_program = PushProgram(copy.deepcopy(program.code))
            new_genome.methods[method_name] = new_program
        new_genome.fitness = self.fitness
        new_genome.accuracy = self.accuracy
        new_genome.method_accuracies = self.method_accuracies.copy()
        new_genome.complexity_penalty = self.complexity_penalty
        return new_genome

class PushGPInterpreter:
    """ interpreter with better method execution"""
    
    def __init__(self, profile: str = 'primitives_full', max_steps: int = 150):
        self.profile = profile
        self.max_steps = max_steps
        self.instruction_set = create__pushgp_instruction_set(profile)
        self.instruction_list = list(self.instruction_set.values())
    
    
    def push_args_to_stacks(self, state: PushState, args: List[Any], types: List[str]):
        # If type metadata is available, use it; otherwise infer from Python types
        if types:
            for arg, type_str in zip(args, types):
                t = (type_str or "").lower()
                if t in {"int", "java.lang.integer", "byte", "java.lang.byte", "short", "java.lang.short", "long", "java.lang.long"}:
                    state.integer_stack.append(int(arg))
                elif t in {"float", "java.lang.float", "double", "java.lang.double"}:
                    state.float_stack.append(float(arg))
                elif t in {"boolean", "java.lang.boolean"}:
                    state.boolean_stack.append(bool(arg))
                elif t in {"char", "java.lang.character"}:
                    # represent char as 1-length string
                    sval = arg if isinstance(arg, str) else (chr(int(arg)) if isinstance(arg, (int, float)) else str(arg))
                    state.string_stack.append(sval[:1])
                elif t in {"java.lang.string", "string"}:
                    state.string_stack.append(str(arg))
                else:
                    # Fallback by python type
                    if isinstance(arg, bool):
                        state.boolean_stack.append(arg)
                    elif isinstance(arg, int):
                        state.integer_stack.append(arg)
                    elif isinstance(arg, float):
                        state.float_stack.append(arg)
                    elif isinstance(arg, str):
                        state.string_stack.append(arg)
        else:
            for arg in args:
                if isinstance(arg, bool):
                    state.boolean_stack.append(arg)
                elif isinstance(arg, int):
                    state.integer_stack.append(arg)
                elif isinstance(arg, float):
                    state.float_stack.append(arg)
                elif isinstance(arg, str):
                    state.string_stack.append(arg)
    
    
    def execute_sequence(self, genome: PushGPGenome, example: TrainingExample) -> List:
        """Execute each method Push program in a sequence, preserving DS state."""
        state = PushState(max_steps=self.max_steps)
        step_results = []
        used_inputs = []
        for i, method_name in enumerate(example.sequence):
            args = example.input_args[i] if i < len(example.input_args) else []
            arg_types = example.type_inputs[i] if i < len(example.type_inputs) else []
            expected_type = example.type_outputs[i] if i < len(example.type_outputs) else None

            # Reset non-persistent stacks between method calls
            state.result = None
            state.string_stack.clear()
            state.integer_stack.clear()
            state.boolean_stack.clear()
            state.float_stack.clear()
            state.exec_stack.clear()
            state.step_count = 0

            # Push arguments
            self.push_args_to_stacks(state, args, arg_types)

            # Snapshot initial argument stacks to detect usage
            init_int = state.integer_stack.copy()
            init_bool = state.boolean_stack.copy()
            init_str = state.string_stack.copy()
            init_float = state.float_stack.copy()

            # Execute method program (if learned)
            if method_name in genome.methods:
                program = genome.methods[method_name]
                state = program.execute(state)

            # Read result directly based on expected type
            result = self._extract_result_from_state(state, expected_type)
            step_results.append(result)

            # Determine if any initial arguments were consumed (prefix check)
            def _prefix_preserved(init, after):
                return len(init) == 0 or (len(after) >= len(init) and after[:len(init)] == init)
            used = not (
                _prefix_preserved(init_int, state.integer_stack)
                and _prefix_preserved(init_bool, state.boolean_stack)
                and _prefix_preserved(init_str, state.string_stack)
                and _prefix_preserved(init_float, state.float_stack)
            )
            # If no inputs existed at all, mark as used to avoid penalizing
            if not (init_int or init_bool or init_str or init_float):
                used = True
            used_inputs.append(used)
        return step_results, used_inputs


    def _extract_result_from_state(self, state: "PushState", expected_type: str):
        """Return strictly typed results; treat error/null explicitly."""
        if expected_type is None:
            return None
        if expected_type == "null":
            return None
        if expected_type == "error":
            if state.error_stack and state.error_stack[-1] == "error":
                return "error"
            return None

        type_map = {
            # Integers family
            "int": state.integer_stack,
            "java.lang.integer": state.integer_stack,
            "byte": state.integer_stack,
            "java.lang.byte": state.integer_stack,
            "short": state.integer_stack,
            "java.lang.short": state.integer_stack,
            "long": state.integer_stack,
            "java.lang.long": state.integer_stack,
            # Floats family (float/double)
            "float": state.float_stack,
            "java.lang.float": state.float_stack,
            "double": state.float_stack,
            "java.lang.double": state.float_stack,
            # Booleans
            "boolean": state.boolean_stack,
            "java.lang.boolean": state.boolean_stack,
            # Strings/Chars
            "java.lang.string": state.string_stack,
            "string": state.string_stack,
            "char": state.string_stack,
            "java.lang.character": state.string_stack,
        }
        # normalize expected_type for lookup
        if isinstance(expected_type, str):
            key = expected_type.lower()
        else:
            key = None
        stack = type_map.get(key)
        if stack and len(stack) > 0:
            return stack[-1]
        return None



    
    def random_program(self, max_depth: int = 3, max_length: int = 8) -> List:
        """Generate random program with bias toward useful instructions"""
        if max_depth <= 0 or random.random() < 0.6:
            # Terminal: single instruction
            return [random.choice(self.instruction_list)]
        
        # Non-terminal: list of instructions/sublists
        length = random.randint(1, min(max_length, 4))
        program = []
        
        for _ in range(length):
            if random.random() < 0.7:  # Favor single instructions
                program.append(self._get_random_instruction())
            else:
                # Add subprogram
                subprogram = self.random_program(max_depth - 1, max_length // 2)
                program.append(subprogram)
        
        return program

    def _get_random_instruction(self):
        """Get a random instruction, creating new ERCs when selected"""
        instr = random.choice(self.instruction_list)
    
        # If it's an ERC class, create a new instance with a new random value
        if isinstance(instr, (ERC_INT, ERC_FLOAT)):
            return instr.__class__()  # Create fresh instance
    
        return instr
    
    def create_smart_initial_program(self, method_name: str) -> List:
        """Create smarter initial programs based on method name"""
        m = method_name.lower()
        if m == 'add':
            # Append at end: size -> index, then insert(value) at index
            return [
                self.instruction_set['DS.SIZE'],
                self.instruction_set['DS.INSERT.AT.INDEX'],
                self.instruction_set['BOOL.CONST.True']
            ]
        if m == 'isEmpty':
            # Append at end: size -> index, then insert(value) at index
            return [
                self.instruction_set['DS.SIZE'],
                self.instruction_set['INT.CONST.0'],
                self.instruction_set['INT.EQ']
            ]
        
        
        return self.random_program(max_depth=2, max_length=5)
    

def _validate_evolution_params(training_data: List[TrainingExample], population_size: int, generations: int):
    """Validate evolution parameters"""
    if not training_data:
        raise ValueError("Training data cannot be empty")
    if generations <= 0:
        raise ValueError("Number of generations must be greater than 0")
    if population_size <= 0:
        raise ValueError("Population size must be greater than 0")

def _extract_method_names(training_data: List[TrainingExample]) -> List[str]:
    """Extract unique method names from training data"""
    method_names = set()
    for example in training_data:
        for call_str in example.sequence:
            method_name = call_str
            method_names.add(method_name)
    return list(method_names)


def serialize_program(code):
        """Convert program to serializable format"""
        result = []
        for item in code:
            if hasattr(item, 'name'):  # PushInstruction
                result.append(item.name)
            elif isinstance(item, list):
                result.append(serialize_program(item))
            else:
                result.append(str(item))
        return result

def run_pushgp_evolution(training_data: List[TrainingExample],
                        population_size: int = 100,
                        generations: int = 300,
                        no_improve_generations: int = 100,
                        profile: str = 'primitives_full',
                        processes: Optional[int] = None,
                        log_every: int = 25,
                        max_steps: Optional[int] = None) -> PushGPGenome:
    
    _validate_evolution_params(training_data, population_size, generations)
    
    if processes is None:
        processes = min(population_size, os.cpu_count() or 2)
    if max_steps is None:
        max_steps = 80
    
    interpreter = PushGPInterpreter(profile=profile, max_steps=max_steps)
    method_names = _extract_method_names(training_data)

    
    print(f"Learning PushGP programs for {len(method_names)} methods: {method_names}")
    

    population = []
    for _ in range(population_size):
        genome = PushGPGenome()
        for method_name in method_names:
            if random.random() < 0:  
                program_code = interpreter.create_smart_initial_program(method_name)
            else:
                program_code = interpreter.random_program(max_depth=2, max_length=10)
            
            program = PushProgram(program_code)
            genome.add_method(method_name, program)
        population.append(genome)
    
    best_genome = None
    best_fitness = float('inf')
    stall_count = 0
    with ProcessPoolExecutor(
        max_workers=max(1, min(processes, population_size)),
        initializer=init_worker,
        initargs=(training_data, interpreter)
    ) as executor:
        
        for generation in range(generations):
            # Parallel evaluation - only pass genome and threshold now
            early_threshold = best_fitness if best_genome else None
            
            population = list(executor.map(
                evaluate_wrapper,
                [(g, early_threshold) for g in population]
            ))
        
        
            if generation % 10 == 0 and generation > 0:
                population = maintain_diversity(population, training_data, interpreter)

            # Sort and track best
            population.sort(key=lambda x: x.fitness)

            if population[0].fitness < best_fitness:
                best_fitness = population[0].fitness
                best_genome = population[0].copy()
                stall_count = 0
            else:
                stall_count += 1

            # Progress logging
            if generation % log_every == 0:
                best = population[0]
                print(f"Gen {generation}: Fitness={best.fitness:.6f}, "
                      f"Acc={best.accuracy:.3f}, Complexity={best.complexity_penalty:.3f}")
                for method_name, program in best.methods.items():
                    print(f"  {method_name}: {serialize_program(program.code)}")

            # Early stopping
            if population[0].accuracy >= 0.99 and population[0].fitness < 0.02:
                print(f"Solution found at generation {generation}")
                break
            
            if stall_count >= no_improve_generations:
                print(f"Stopping after {no_improve_generations} gens without improvement")
                break

            
            new_population = []

            # Elitism (keep top 10%)
            elite_count = max(2, population_size // 10)
            new_population.extend([g.copy() for g in population[:elite_count]])

            # Generate offspring
            while len(new_population) < population_size:
                if random.random() < 0.5:  # Crossover
                    parent1 = tournament_selection(population, 8) 
                    parent2 = tournament_selection(population, 8)
                    offspring = crossover_genomes(parent1, parent2)
                else:  # Clone + mutate
                    parent = tournament_selection(population, 8)
                    offspring = parent.copy()


                adaptive_mutate_genome(offspring, interpreter, generation, generations, stall_count)
                new_population.append(offspring)

            population = new_population
    
    return best_genome

def evaluate_wrapper(args):
    global GLOBAL_TRAINING_DATA, GLOBAL_INTERPRETER
    genome, early_threshold = args 
    return evaluate_genome(genome, GLOBAL_TRAINING_DATA, GLOBAL_INTERPRETER, early_stop_threshold=early_threshold)

def evaluate_genome(genome: PushGPGenome, training_data, interpreter, early_stop_threshold: Optional[float] = None):
    total_error = 0.0
    total_examples = 0
    correct_predictions = 0
    method_stats = defaultdict(lambda: {'correct': 0, 'total': 0, 'downstream_correct': 0, 'downstream_total': 0})
    abort_sum = None
    if early_stop_threshold is not None:
        abort_sum = early_stop_threshold * len(training_data)
    
    for example in training_data:
        try:
            predicted_outputs, used_inputs = interpreter.execute_sequence(genome, example)
            # Calculate per-call correctness
            call_correct = []
            for pred, exp in zip_longest(predicted_outputs, example.expected_outputs, fillvalue=None):
                is_correct = _rec_error(pred, exp) < 0.01
                call_correct.append(is_correct)
            
            # Update method stats
            for i, method_name in enumerate(example.sequence):
                is_correct = call_correct[i] if i < len(call_correct) else False
                
                # Direct accuracy
                method_stats[method_name]['correct'] += int(is_correct)
                method_stats[method_name]['total'] += 1
                
                # Downstream accuracy: if this call is correct, how many later calls are correct?
                if is_correct and i + 1 < len(call_correct):
                    downstream_calls = call_correct[i + 1:]
                    method_stats[method_name]['downstream_correct'] += sum(downstream_calls)
                    method_stats[method_name]['downstream_total'] += len(downstream_calls)
     
            genome_error = aggregate_genome_error(
                example.sequence, predicted_outputs, example.expected_outputs
            )
            
            # Penalties
            unused_pen = compute_arg_unused_penalty(example.sequence, used_inputs, example.input_args)
            fitness_error = min(1.0, genome_error + 0.1 * unused_pen)  
            
            total_error += fitness_error
            total_examples += 1
            
            if genome_error < 0.01:
                correct_predictions += 1
            
            # Early abort
            if abort_sum is not None and total_error > abort_sum:
                genome.fitness = 1e5
                genome.accuracy = correct_predictions / total_examples
                genome.complexity_penalty = genome.get_complexity_penalty()
                return genome
                
        except Exception:
            total_error += 1
            total_examples += 1
            for method_name in example.sequence:
                method_stats[method_name]['total'] += 1
    
    base_fitness = total_error / total_examples if total_examples > 0 else 1.0
    complexity_penalty = genome.get_complexity_penalty()
    
 
    genome.fitness = base_fitness + 0.5 * complexity_penalty  
    genome.accuracy = correct_predictions / total_examples if total_examples > 0 else 0.0
    genome.complexity_penalty = complexity_penalty
    
    #method accuracies
    method_accuracies = {}
    for method_name, stats in method_stats.items():
        # Direct accuracy
        direct_acc = stats['correct'] / max(1, stats['total'])
        
        # Downstream accuracy (how enabling is this method?)
        if stats['downstream_total'] > 0:
            downstream_acc = stats['downstream_correct'] / stats['downstream_total']
        else:
            downstream_acc = direct_acc  # No downstream calls, use direct
        
        # Weighted combination: direct accuracy is primary, downstream is a bonus
        # This rewards methods that are both correct AND enable correct behavior
        combined_acc = 0.7 * direct_acc + 0.3 * downstream_acc
        method_accuracies[method_name] = combined_acc
    genome.method_accuracies = method_accuracies

    return genome




def tournament_selection(population: List[PushGPGenome], tournament_size: int) -> PushGPGenome:
    """Tournament selection"""
    tournament = random.sample(population, min(tournament_size, len(population)))
    return min(tournament, key=lambda x: x.fitness)

def crossover_genomes(parent1: PushGPGenome, parent2: PushGPGenome) -> PushGPGenome:
    """ crossover"""
    offspring = PushGPGenome()
    
    all_methods = set(parent1.methods.keys()) | set(parent2.methods.keys())
    
    for method_name in all_methods:
        if method_name in parent1.methods and method_name in parent2.methods:
            # Choose better parent or crossover
            acc1 = parent1.method_accuracies.get(method_name, 0)
            acc2 = parent2.method_accuracies.get(method_name, 0)
            
            if random.random() < 0.8:  # favor crossover
                program1 = parent1.methods[method_name].code
                program2 = parent2.methods[method_name].code
                new_code = crossover_programs(program1, program2)
            else:
                new_code = parent1.methods[method_name].code if acc1 >= acc2 else parent2.methods[method_name].code
                new_code = copy.deepcopy(new_code)
        elif method_name in parent1.methods:
            new_code = copy.deepcopy(parent1.methods[method_name].code)
        else:
            new_code = copy.deepcopy(parent2.methods[method_name].code)
        
        offspring.add_method(method_name, PushProgram(new_code))
    
    return offspring

def crossover_programs(program1: List, program2: List) -> List:
    """ program crossover"""
    if not program1 or not program2:
        return program1 if program1 else program2
    
    # Multiple crossover strategies
    strategy = random.choice(['single_point', 'uniform', 'block'])
    
    if strategy == 'single_point':
        point1 = random.randint(0, len(program1))
        point2 = random.randint(0, len(program2))
        return program1[:point1] + program2[point2:]
    elif strategy == 'uniform':
        max_len = max(len(program1), len(program2))
        result = []
        for i in range(max_len):
            if i < len(program1) and i < len(program2):
                result.append(program1[i] if random.random() < 0.5 else program2[i])
            elif i < len(program1):
                result.append(program1[i])
            elif i < len(program2):
                result.append(program2[i])
        return result
    else:  # block
        # Take blocks from each parent
        mid1 = len(program1) // 2
        mid2 = len(program2) // 2
        return program1[:mid1] + program2[mid2:]

def adaptive_mutate_genome(genome: PushGPGenome, interpreter: PushGPInterpreter,
                          generation: int, max_generations: int, stall_count: int,
                          base_rate: float = 0.4):
    """genome mutation"""
    # High early exploration, low late refinement
    progress = generation / max(1, max_generations)
    mutation_rate = base_rate * (1.0 - 0.5 * progress)  # Drops to 50% of base
    

    for method_name, program in genome.methods.items():
        if len(program.code) == 0:
                program.code = interpreter.random_program(max_depth=2, max_length=8)
                continue
        if random.random() < mutation_rate:
            # Choose mutation type based on program quality
            acc = genome.method_accuracies.get(method_name, 0.0)
            if stall_count >25 and acc > 0.5:
                # If stalled, increase mutation aggressiveness
                mutate_program_aggressive(program.code, interpreter)
                continue
            if acc < 0.4:
                # Poor performance: major changes
                mutate_program_aggressive(program.code, interpreter)
            elif acc < 0.98:
                # Medium performance: moderate changes
                mutate_program(program.code, interpreter, mutation_rate=0.4)
            else:
                # Good performance: minor tweaks only
                if random.random()<0.5:
                    mutate_program_conservative(program.code, interpreter)
                else:
                    mutate_program(program.code, interpreter, mutation_rate=0.2)

def mutate_program_aggressive(program: List, interpreter: PushGPInterpreter):
    """Aggressive mutation for poor performers"""
    # Replace large chunks
    if random.random() < 0.5:
        replacement = interpreter.random_program(max_depth=2, max_length=5)
        if len(program) > 2:
            start = random.randint(0, len(program) - 2)
            end = random.randint(start + 1, len(program))
            program[start:end] = replacement
        else:
            program[:] = replacement
    else:
        # Replace multiple random instructions
        for i in range(len(program)):
            if random.random() < 0.5:
                program[i] = random.choice(interpreter.instruction_list)

def mutate_program_conservative(program: List, interpreter: PushGPInterpreter):
    """Conservative mutation for good performers"""
    if not program:
        return
    
    mutation_type = random.choice(['swap', 'tweak_constant', 'insert'])
    
    if mutation_type == 'swap' and len(program) >= 2:
        # Swap two adjacent instructions
        i = random.randint(0, len(program) - 2)
        program[i], program[i+1] = program[i+1], program[i]
    
    elif mutation_type == 'tweak_constant':
        # Modify a constant slightly
        for i, instr in enumerate(program):
            if hasattr(instr, 'value') and isinstance(instr.value, int):
                if random.random() < 0.3:
                    delta = random.choice([-1, 0, 1])
                    new_val = instr.value + delta
                    if hasattr(instr, '__class__'):
                        program[i] = instr.__class__(new_val)
    
    elif mutation_type == 'insert' and len(program) < 10:
        # Insert single instruction
        pos = random.randint(0, len(program))
        program.insert(pos, random.choice(interpreter.instruction_list))

def mutate_program(program: List, interpreter: PushGPInterpreter, mutation_rate: float = 0.4):
    """ program mutation"""

    if len(program) == 0:
        if random.random() < 0.8:
            # Add several instructions
            num_to_add = random.randint(2, 5)
            for _ in range(num_to_add):
                program.append(interpreter._get_random_instruction())
        return
    def mutate_recursive(prog):
        for i, item in enumerate(prog):
            if random.random() < mutation_rate:
                if isinstance(item, list):
                    if random.random() < 0.5:
                        mutate_recursive(item)
                    else:
                        # Replace with single instruction
                        prog[i] = random.choice(interpreter.instruction_list)
                else:
                    if random.random() < 0.7:
                        # Replace with random instruction
                        prog[i] = random.choice(interpreter.instruction_list)
                    else:
                        # Replace with small subprogram
                        subprog = interpreter.random_program(max_depth=2, max_length=3)
                        prog[i] = subprog
            elif isinstance(item, list):
                mutate_recursive(item)
    
    # Structural mutations
    if random.random() < mutation_rate:
        if len(program) > 1 and random.random() < 0.4:
            # Remove instruction
            program.pop(random.randint(0, len(program) - 1))
        elif len(program) < 8 and random.random() < 0.5:
            # Add instruction
            pos = random.randint(0, len(program))
            program.insert(pos, random.choice(interpreter.instruction_list))
    
    mutate_recursive(program)

def _calculate_behavioral_signature(genome: PushGPGenome, 
                                   training_data: List[TrainingExample],
                                   interpreter: PushGPInterpreter,
                                   sample_size: int = 5) -> tuple:
    """Create behavioral signature for diversity measurement"""
    signature = []
    samples = random.sample(training_data, min(sample_size, len(training_data)))
    
    for example in samples:
        try:
            predicted, _, _ = interpreter.execute_sequence(genome, example)
            # Hash the outputs
            sig = tuple(str(p) for p in predicted)
            signature.append(sig)
        except:
            signature.append(None)
    
    return tuple(signature)


def maintain_diversity(population: List[PushGPGenome],
                      training_data: List[TrainingExample],
                      interpreter: PushGPInterpreter,
                      diversity_threshold: float = 0.3) -> List[PushGPGenome]:
    """Ensure population maintains behavioral diversity"""
    if len(population) < 10:
        return population
    
    # Calculate signatures
    signatures = [_calculate_behavioral_signature(g, training_data, interpreter) 
                  for g in population]
    
    # Keep diverse individuals
    diverse_pop = [population[0]]  # Keep best
    diverse_sigs = [signatures[0]]
    
    for genome, sig in zip(population[1:], signatures[1:]):
        # Check if sufficiently different from existing
        is_diverse = True
        for existing_sig in diverse_sigs:
            similarity = sum(1 for a, b in zip(sig, existing_sig) if a == b) / len(sig)
            if similarity > (1 - diversity_threshold):
                is_diverse = False
                break
        
        if is_diverse:
            diverse_pop.append(genome)
            diverse_sigs.append(sig)
        elif len(diverse_pop) < len(population) * 0.8:
            # Still accept some similar ones to maintain population size
            diverse_pop.append(genome)
            diverse_sigs.append(sig)
    
    return diverse_pop


def _string_error(a: str, b: str) -> float:
    if a == b:
        return 0.0
    if _levenshtein:
        dist = _levenshtein(a, b)
        denom = max(len(a), len(b), 1)
        return min(dist / denom, 1.0)
    # fallback: difflib ratio -> distance
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return 1.0 - ratio

def _numeric_error(pred: float, exp: float) -> float:
    if math.isclose(pred, exp, rel_tol=1e-9, abs_tol=EPS):
        return 0.0
    denom = max(abs(exp), 1.0)
    return min(abs(pred - exp) / denom, 1.0)

def _rec_error(pred: Any, exp: Any) -> float:
    # None handling
    if pred is None and exp is None:
        return 0.0
    if pred is None or exp is None:
        return 1.0
    def is_number(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)
    # Type mismatch -> full penalty except numeric cross-types
    if type(pred) != type(exp):
        if is_number(pred) and is_number(exp):
            pass
        else:
            return 1.0

    # Booleans: exact
    if isinstance(exp, bool):
        return 0.0 if pred == exp else 1.0

    # Numbers
    if isinstance(exp, (int, float)) and isinstance(pred, (int, float)):
        return _numeric_error(float(pred), float(exp))

    # Strings
    if isinstance(exp, str) and isinstance(pred, str):
        return _string_error(pred, exp)


    # Fallback to exact string equality
    try:
        return 0.0 if pred == exp else 1.0
    except Exception:
        return 1.0

def calculate_per_call_errors(sequence: List[str], predicted: List[Any], expected: List[Any]) -> List[float]:
    """Return list of per-call errors aligned to 'sequence' length (zip_longest)."""
    errs = []
    for _, p, e in zip_longest(sequence, predicted, expected, fillvalue=None):
        errs.append(_rec_error(p, e))
    return errs


def aggregate_genome_error(sequence: List[str],
                           predicted: List[Any],
                           expected: List[Any]) -> float:
    if not sequence:
        return 0.0

    per_call = calculate_per_call_errors(sequence, predicted, expected)
    
    # Exponential penalty for errors
    exp_errors = [err ** 0.5 for err in per_call]  # sqrt makes small errors less costly
    
    # Group by method name
    grouped = defaultdict(list)
    for name, err in zip(sequence, exp_errors):
        grouped[name].append(err)
    
    # Average per method
    method_errors = [sum(errs)/len(errs) for errs in grouped.values()]
    # Weight recent errors more heavily (they depend on earlier correctness)
    weights = [1.0 + i * 0.1 for i in range(len(method_errors))]
    total_w = sum(weights)
    weighted_mean = sum(e * w for e, w in zip(method_errors, weights)) / total_w
    
    return float(max(0.0, min(1.0, weighted_mean)))




def compute_arg_unused_penalty(sequence: List[str], used_inputs: List[bool], input_args: List[List[Any]]) -> float:
    """Penalize calls that ignore all of their input arguments.
    Returns value in [0..1]. Weight applied per unused call.
    """
    if not sequence or not used_inputs:
        return 0.0
    # weight controls strength of penalty per unused call
    weight = 0.3
    misses = 0
    total = 0
    for used, args in zip_longest(used_inputs, input_args, fillvalue=[]):
        if args:  # only penalize when arguments exist
            total += 1
            if not used:
                misses += 1
    if total == 0 or misses == 0:
        return 0.0
    return min(1.0, weight * misses / max(1, len(sequence)))


