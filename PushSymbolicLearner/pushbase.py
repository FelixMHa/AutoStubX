import random
import copy
from typing import Dict, List, Any, Union, Optional
from trainingexample import TrainingExample
import math

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
        new_state.map_storage = copy.deepcopy(self.map_storage)
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


class PushProgram:
    """ Push program with better execution"""
    
    def __init__(self, code: List[Union[PushInstruction, List]]):
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
        self._behavioral_signature: Optional[tuple] = None
        self.case_errors: List[float] = []
    
    def add_method(self, method_name: str, program: PushProgram):
        """Add method program to genome"""
        self.methods[method_name] = program
    
    def get_complexity_penalty(self) -> float:
        """Calculate complexity penalty"""
        total_complexity = 0
        for program in self.methods.values():
            total_complexity += self._count_instructions(program.code)
        return total_complexity
    
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
        new_genome._behavioral_signature = self._behavioral_signature
        new_genome.case_errors = self.case_errors.copy()
        return new_genome

    def invalidate_signature(self):
        """Call after any mutation or crossover."""
        self._behavioral_signature = None

class PushProgram:
    """ Push program with better execution"""
    
    def __init__(self, code: List[Union[PushInstruction, List]]):
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
        instructions.extend([DUP_ANY(),SWAP_ANY(), POP_ANY(), ITE()])
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
    
    
    def execute_sequence(self, genome: PushGPGenome, example: TrainingExample) -> tuple[List, List]:
        """Execute each method Push program in a sequence, preserving DS state."""
        state = PushState(max_steps=self.max_steps)
        step_results = []
        used_inputs = []
        for i, method_name in enumerate(example.sequence):
            args = example.input_args[i] if i < len(example.input_args) else []
            arg_types = example.type_inputs[i] if i < len(example.type_inputs) else []
            expected_type: Optional[str] = example.type_outputs[i] if i < len(example.type_outputs) else None

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


    def _extract_result_from_state(self, state: "PushState", expected_type: Optional[str]):
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
        stack = type_map.get(key) if key is not None else None
        if stack and len(stack) > 0:
            return stack[-1]
        return None

    def random_program(self, max_depth: int = 2, max_length: int = 5) -> List:
        """Generate linear programs biased toward useful patterns"""
        if max_depth <= 0 or random.random() < 0.9:  # 90% flat lists
            length = random.randint(1, max_length)
            return [self._get_random_instruction() for _ in range(length)]

        # Rare: add one sublist
        program = [self._get_random_instruction() for _ in range(random.randint(1, 3))]
        program.append(self.random_program(max_depth - 1, 3))
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
        if m == 'add#obj':

            return [
                self.instruction_set['DS.SIZE'],
                self.instruction_set['DS.INSERT.AT.INDEX'],
                self.instruction_set['BOOL.CONST.True']
            ]
        if m == 'empty#0':
 
            return [
                self.instruction_set['DS.SIZE'],
                self.instruction_set['INT.CONST.0'],
                self.instruction_set['INT.EQ']
            ]
        if m == 'push#obj':

            return [
                self.instruction_set['DUP.ANY'],
                self.instruction_set['DS.SIZE'],
                self.instruction_set['DS.INSERT.AT.INDEX']
            ]
        if m == 'pop#0':

            return [
                self.instruction_set['DS.SIZE'],
                self.instruction_set['INT.CONST.1'],
                self.instruction_set['INT.SUB'],
                self.instruction_set['DUP.ANY'],
                self.instruction_set['DS.GET.INDEX'],
                self.instruction_set['SWAP.ANY'],
                self.instruction_set['DS.REMOVE.INDEX']
            ]


        if m == 'peek#0':

            return [
                self.instruction_set['DS.SIZE'],
                self.instruction_set['INT.CONST.1'],
                self.instruction_set['INT.SUB'],
                self.instruction_set['DS.GET.INDEX']
            
        ]
        
        
        return self.random_program(max_depth=2, max_length=6)  

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
            state.integer_stack.append(abs(_int))



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
    def __init__(self, value: Optional[int] = None):
        if value is None:
            value = int(random.uniform(-10, 256))
        super().__init__(f"ERC.INT.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.integer_stack.append(self.value)
        
class ERC_FLOAT(PushInstruction):
    def __init__(self, value: Optional[float] = None):
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
            count = max(0, min(count, 50))
            block = state.exec_stack.pop()
            for _ in range(count):
                state.exec_stack.append(block)

#Utility Instructions
class DUP_ANY(PushInstruction):
    def __init__(self):
        super().__init__("DUP.ANY")

    def execute(self, state: PushState):
        for stack in [state.integer_stack, state.boolean_stack,
                      state.string_stack, state.float_stack]:
            if stack:  # first non-empty stack
                stack.append(stack[-1])
                return

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

class ITE(PushInstruction):
    def __init__(self):
        super().__init__("ITE")

    def execute(self, state: PushState):
        if state.boolean_stack:
            cond = state.boolean_stack.pop()
            if len(state.exec_stack) >= 2:
                false_val = state.exec_stack.pop()
                true_val = state.exec_stack.pop()
                state.exec_stack.append(true_val if cond else false_val)

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
                state.data_structure_stack[index] = value

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
                else:
                    state.error_stack.append("error")



class DS_REMOVE_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.REMOVE.INDEX")

    def execute(self, state: PushState):
        if state.integer_stack:
            index = state.integer_stack.pop()
            if 0 <= index < len(state.data_structure_stack):
                state.data_structure_stack.pop(index)
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
                index = next((i for i,v in enumerate(reversed(state.data_structure_stack)) if v == value), -1)
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