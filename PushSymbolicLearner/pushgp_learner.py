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

    
EPS = 1e-9
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


class STR_IF(PushInstruction):
    def __init__(self):
        super().__init__("STR_IF")

    def execute(self, state: PushState):
        if state.boolean_stack and len(state.string_stack) >= 2:
            false_val = state.string_stack.pop()
            true_val = state.string_stack.pop()
            cond = state.boolean_stack.pop()
            state.string_stack.append(true_val if cond else false_val)


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
            INT_GT(),
        ])
        for i in range(-2, 4):
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
            DS_SIZE(), DS_IS_EMPTY(), DS_CLEAR(),
            DS_GET_INDEX(), DS_SET_INDEX(),
            DS_INSERT_AT_INDEX(), DS_REMOVE_INDEX(),
            DS_LAST_INDEX(), DS_FIRST_INDEX(),
            DS_CONTAINS(), DS_PEEK_LAST(), DS_POP_LAST(),
        ])
        return {instr.name: instr for instr in instructions}

    # Default: primitives_full
    instructions = []

    # Core integers (include linear + multiplicative ops for regression)
    instructions.extend([
        INT_ADD(), INT_SUB(), INT_MUL(), INT_DIV(),
        INT_EQ(), INT_GT(), INT_LT(),
        INT_NEG(), INT_MOD(), ITE_INT(),
    ])
    for i in range(-4, 7):
        instructions.append(INT_CONST(i))

    # Floats
    instructions.extend([
        FLOAT_ADD(), FLOAT_SUB(), FLOAT_MUL(), FLOAT_DIV(),
        FLOAT_NEG(), FLOAT_ABS(), FLOAT_FLOOR(),
        FLOAT_COS(), FLOAT_LT(), FLOAT_GT(), FLOAT_EQ(), ITE_FLOAT(),
        FLOAT_TO_STR(), STR_TO_FLOAT(), FLOAT_IS_NAN(), FLOAT_IS_INF(),
        FLOAT_IS_FINITE(),
    ])
    for f in [0.0, 1.0, -1.0, 2.0, 0.5]:
        instructions.append(FLOAT_CONST(f))

    # Booleans
    instructions.extend([
        BOOL_AND(), BOOL_OR(), BOOL_NOT(), BOOL_XOR(),
        BOOL_TO_INT(), ITE_BOOL(),
    ])

    instructions.extend([
        BOOL_CONST(True), BOOL_CONST(False),
    ])

    # Bit
    instructions.extend([
        BIT_AND(), BIT_OR(), BIT_XOR(),   
        BIT_NOT(), BIT_SHL(), BIT_SHR(),      
    ])

    # Strings (minimal core)
    instructions.extend([
        STR_CONCAT(), STR_EQ(), STR_LEN(), STR_CHAR_AT(),    
        STR_STARTS_WITH(), STR_CONTAINS(), STR_INDEX_OF(),   
        STR_SUBSTRING(), STR_REPLACE(), STR_REPLACE_ALL(),
        STR_TO_INT(), INT_TO_STR(), ASCII_TO_STR(), STR_TO_ASCII(),   
        STR_TO_LOWER(), STR_TO_UPPER(), STR_TRIM(), STR_IF(),         
    ])

    # Utilities helpful for expression building
    instructions.extend([DUP_ANY(), SWAP_ANY(), POP_ANY()])

    return {instr.name: instr for instr in instructions}


class PushProgram:
    """ Push program with better execution"""
    
    def __init__(self, code: List[Union[PushInstruction, List]] = None):
        self.code = code or []
    
    def execute(self, state: PushState, method_args: List[Any] = None):
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
        return total_complexity * 0.005  # Small penalty to allow complex solutions
    
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
        ds_states =  []
        ds_states.append([])
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
            ds_states.append(copy.deepcopy(state.data_structure_stack))

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
        return step_results, ds_states, used_inputs


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
        stack = type_map.get(expected_type)
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
                program.append(random.choice(self.instruction_list))
            else:
                # Add subprogram
                subprogram = self.random_program(max_depth - 1, max_length // 2)
                program.append(subprogram)
        
        return program
    
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
        if m == 'empty':
            # Append at end: size -> index, then insert(value) at index
            return [
                self.instruction_set['DS.IS_EMPTY'],
            ]
        if m == 'peek':
            # Append at end: size -> index, then insert(value) at index
            return [
                self.instruction_set['DS.PEEK.LAST'],
            ]
        if m == 'pop':
            # Append at end: size -> index, then insert(value) at index
            return [
                self.instruction_set['DS.POP.LAST'],
            ]
        if m == 'push':
            # Append at end: size -> index, then insert(value) at index
            return [
                self.instruction_set['DS.SIZE'],
                self.instruction_set['DS.INSERT.AT.INDEX'],
                self.instruction_set['DS.PEEK.LAST']
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

def get_mutators(training_data: List["TrainingExample"]) -> List[str]:

    method_inputs = defaultdict(list)
    method_outputs = defaultdict(list)

    for ex in training_data:
        for method, inputs, output in zip(ex.sequence, ex.input_args, ex.expected_outputs):
            method_inputs[method].append(inputs)
            method_outputs[method].append(output)

    mutators = []
    for method in method_outputs.keys():
        outs = method_outputs[method]
        norm_outs = [str(o) if o is not None else "None" for o in outs]
        unique_outs = set(norm_outs)

        # Heuristic 1 — trivial return values
        if unique_outs <= {"None", "True", "False"} and len(unique_outs) == 1:
            mutators.append(method)
            continue

        # Heuristic 2 — output equals one of its inputs (like remove(E) → E)
        io_match_count = 0
        total = 0
        for inputs, output in zip(method_inputs[method], method_outputs[method]):
            if not inputs:
                continue
            total += 1
            if any(str(arg) == str(output) for arg in inputs):
                io_match_count += 1
        if total > 0 and io_match_count / total > 0.5:
            mutators.append(method)
            continue


    return sorted(set(mutators))

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
        try:
            processes = min(population_size, os.cpu_count() or 2)
        except Exception:
            processes = min(population_size, 2)
    if max_steps is None:
        max_steps = 80

    interpreter = PushGPInterpreter(profile=profile, max_steps=max_steps)
    method_names = _extract_method_names(training_data)
    mutators = get_mutators(training_data)
    
    print(f"Learning PushGP programs for {len(method_names)} methods: {method_names}")
    
    # Create initial population with smarter initialization
    population = []
    for _ in range(population_size):
        genome = PushGPGenome()
        for method_name in method_names:
            # Use smart initialization (70% smart, 30% random)
            if random.random() < 0:
                program_code = interpreter.create_smart_initial_program(method_name)
            else:
                program_code = interpreter.random_program(max_depth=2, max_length=5)
            
            program = PushProgram(program_code)
            genome.add_method(method_name, program)
        population.append(genome)
    
    # Evolution loop
    best_genome = None
    best_fitness = float('inf')
    stall_count = 0
    
    for generation in range(generations):
    

        # Early-abort threshold based on previous best (ignore complexity for bound)
        early_threshold = None if best_genome is None else best_fitness

        # Parallel evaluation of population
        with ProcessPoolExecutor(max_workers=max(1, min(processes, population_size))) as executor:
            population = list(executor.map(
                evaluate_wrapper,
                [(g, training_data, interpreter, mutators, early_threshold) for g in population]
            ))
        
        # Track best genome
        population.sort(key=lambda x: x.fitness)
        if population[0].fitness < best_fitness:
            best_fitness = population[0].fitness
            best_genome = population[0].copy()
            stall_count = 0
        else:
            stall_count += 1
        
        # Progress report
        if generation % max(1, log_every) == 0:
            best = population[0]
            print(f"Generation {generation}: Best fitness: {best.fitness:.6f}, "
                  f"accuracy: {best.accuracy:.3f}, complexity: {best.complexity_penalty:.3f}")
            print("Genome methods:")
            for method_name, program in best.methods.items():
                serialized = serialize_program(program.code)
                print(f"{method_name}: {serialized}")
        
        # Early stopping
        if population[0].accuracy == 1.0:
            if best_fitness < 0.02:
                print(f"Early stopping at generation {generation}")
                break
        
        if stall_count >= no_improve_generations:
            print(f"No improvement for {no_improve_generations} generations. Stopping at generation {generation}.")
            break
        
        # Create next generation
        new_population = []
        
        # Elitism
        elite_count = max(1, population_size // 10)
        new_population.extend([genome.copy() for genome in population[:elite_count]])
        
        # Generate offspring
        while len(new_population) < population_size:
            if random.random() < 0.7:  # Crossover
                parent1 = tournament_selection(population, 3)
                parent2 = tournament_selection(population, 3)
                offspring = crossover_genomes(parent1, parent2)
            else:  # Mutation only
                parent = tournament_selection(population, 3)
                offspring = parent.copy()
            
            # Mutate with decaying mutation rate
            base_rate = 0.8
            min_rate = 0.5
            frac = generation / max(1, generations - 1)
            current_mutation_rate = max(min_rate, base_rate * (1.0 - 0.7 * frac))
            mutate_genome(offspring, interpreter, mutation_rate=current_mutation_rate)
            new_population.append(offspring)
        
        population = new_population
    
    return best_genome

def evaluate_wrapper(args):
    genome, training_data, interpreter, mutators, early_threshold = args
    return evaluate_genome(genome, training_data, interpreter, mutators, early_stop_threshold=early_threshold)

def evaluate_genome(genome: PushGPGenome, training_data, interpreter, mutators, early_stop_threshold: Optional[float] = None):
    total_error = 0.0
    total_examples = 0
    correct_predictions = 0

    # Precompute abort sum bound if threshold provided
    abort_sum = None
    if early_stop_threshold is not None:
        abort_sum = early_stop_threshold * max(1, len(training_data))
    
    for example in training_data:
        try:
            predicted_outputs, ds_states, used_inputs = interpreter.execute_sequence(genome, example)
            genome_error = aggregate_genome_error(example.sequence, predicted_outputs, example.expected_outputs)

            # Invariant and empty-case penalties
            inv_pen = compute_invariant_penalty(example.sequence, predicted_outputs, example.expected_outputs, ds_states)
            unused_pen = compute_arg_unused_penalty(example.sequence, used_inputs, example.input_args)

            #mutator_bonus = compute_mutator_bonus(example.sequence, predicted_outputs, example.expected_outputs, mutators, ds_states=ds_states)
            fitness_error = min(1.0, genome_error + inv_pen + unused_pen)

            total_error += fitness_error
            total_examples += 1
            if genome_error < 0.01:
                correct_predictions += 1

            # Early abort: even if remaining examples were perfect, the mean can't drop below threshold
            if abort_sum is not None and total_error > abort_sum:
                # Assign poor fitness and stop evaluation early for this genome
                genome.fitness = 1e5
                genome.accuracy = correct_predictions / total_examples if total_examples > 0 else 0.0
                genome.complexity_penalty = genome.get_complexity_penalty()
                return genome
        except Exception:
            total_error += 1
            total_examples += 1
    
    base_fitness = total_error / total_examples if total_examples > 0 else 1.0
    complexity_penalty = genome.get_complexity_penalty()
    genome.fitness = base_fitness + complexity_penalty
    genome.accuracy = correct_predictions / total_examples if total_examples > 0 else 1.0
    genome.complexity_penalty = complexity_penalty
    
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
            
            if random.random() < 1.0:  # favor crossover
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

def mutate_genome(genome: PushGPGenome, interpreter: PushGPInterpreter, 
                 mutation_rate: float = 0.5):
    """ mutation"""
    for method_name, program in genome.methods.items():
        if random.random() < mutation_rate:
            mutate_program(program.code, interpreter, method_name, mutation_rate)

def mutate_program(program: List, interpreter: PushGPInterpreter, 
                  method_name: str, mutation_rate: float = 0.6):
    """ program mutation"""
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
                        subprog = interpreter.random_program(max_depth=1, max_length=3)
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
                           expected: List[Any],
                           decay: float = 0.9) -> float:
    if not sequence:
        return 0.0

    per_call = calculate_per_call_errors(sequence, predicted, expected)

    # Group errors by call name
    grouped = defaultdict(list)
    for name, err in zip(sequence, per_call):
        grouped[name].append(err)

    # Average error per unique call
    unique_errors = [sum(errs)/len(errs) for errs in grouped.values()]

    # Apply decay weighting across unique calls
    if decay == 1.0:
        call_mean = sum(unique_errors) / len(unique_errors)
    else:
        weights = [decay ** i for i in range(len(unique_errors))]
        total_w = sum(weights)
        call_mean = sum(e * w for e, w in zip(unique_errors, weights)) / total_w

    return float(max(0.0, min(1.0, call_mean)))


def compute_invariant_penalty(sequence: List[str], predicted: List[Any], expected: List[Any], ds_states: List[List[Any]]) -> float:
    """Penalize mutations for methods that must be pure (peekLast/get/size)."""
    violations = 0

    for i, method in enumerate(sequence):
        state = ds_states[i]


        if method == "size":
            reported = predicted[i]
            actual = len(state)
            if reported != actual:
                violations += 1

        if method == "get":
            idx = expected[i] if i < len(expected) else None
            if idx is not None and (idx < 0 or idx >= len(state)):
                violations += 1

        

    # Normalize penalty: fraction of violations, capped at 1.0
    penalty = min(1.0, violations / max(1, len(sequence)))
    return penalty


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

def compute_mutator_bonus(sequence, predicted, expected, mutator_methods, ds_states=None):
    """
    Reward mutators whose effect improves later outputs AND changes DS state.
    Averages per-mutator downstream correctness [0..1].
    """
    bonus = 0.0
    mut_count = 0

    for i, method in enumerate(sequence):
        if method not in mutator_methods:
            continue

        # Reward only if DS actually changed
        state_changed = False
        if ds_states is not None and i < len(ds_states) - 1:
            before, after = ds_states[i], ds_states[i + 1]
            state_changed = before != after  # efficient shallow comparison

        # Skip mutators that didn’t change anything
        if not state_changed:
            continue

        # Look at downstream predictions
        later_pred = predicted[i + 1 :]
        later_exp = expected[i + 1 :]
        if not later_exp:
            continue

        mut_count += 1
        correct = sum(1 for p, e in zip(later_pred, later_exp) if _rec_error(p, e) < 0.01)
        bonus += correct / len(later_exp)

    return bonus / mut_count if mut_count > 0 else 0.0
