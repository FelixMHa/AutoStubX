from typing import List, Union, Dict, Optional

# A symbolic value is just an SMT expression string
Sym = str
Instr = Union[str, List["Instr"]]

class SymbolicState:
    def __init__(self,
                 args: List[str],
                 arr_name: str = "arr",
                 len_name: str = "len",
                 error_val: str = "errorVal"):
        # Typed stacks
        self.int_stack: List[Sym] = []
        self.bool_stack: List[Sym] = []
        self.str_stack: List[Sym] = []
        self.float_stack: List[Sym] = []

        # Data structure context
        self.arr_name = arr_name
        self.len_name = len_name
        self.args = args
        self.error_val = error_val

        # ANY priority (canonical: numeric before boolean/string/float)
        self.any_priority = [
            self.int_stack,
            self.float_stack,
            self.bool_stack,
            self.str_stack,
        ]

    def top_any(self) -> Optional[Sym]:
        for st in self.any_priority:
            if st:
                return st[-1]
        return None

    def push_any(self, value: Sym) -> None:
        # Default: push into int stack if it looks numeric; else bool; else string
        # In practice, you’d route by type info. Here we keep it minimal.
        self.int_stack.append(value)

    def dup_any(self) -> None:
        # Duplicate top of first non-empty stack
        for st in self.any_priority:
            if st:
                st.append(st[-1])
                return

    def pop_any(self) -> None:
        for st in self.any_priority:
            if st:
                st.pop()
                return

    def swap_any(self) -> None:
        for st in self.any_priority:
            if len(st) >= 2:
                st[-1], st[-2] = st[-2], st[-1]
                return


def translate_push_to_smt(program: List[Instr],
                          args: List[str],
                          arr_name: str = "arr",
                          len_name: str = "len",
                          error_val: str = "errorVal") -> Sym:
    """
    Translate a (possibly nested) Push program into an SMT-LIB expression string.
    The final result is the top value on the ANY stack view (first non-empty stack).
    """

    state = SymbolicState(args=args, arr_name=arr_name, len_name=len_name, error_val=error_val)

    def eval_subprog(subprog: List[Instr]) -> Optional[Sym]:
        # Evaluate a nested subprogram and return its final top (ANY view)
        # This pushes intermediate values into stacks by instruction semantics.
        for instr in subprog:
            eval_instr(instr)
        return state.top_any()

    def eval_instr(instr: Instr):
        # Nested subprogram
        if isinstance(instr, list):
            val = eval_subprog(instr)
            if val is not None:
                state.push_any(val)
            return

        # Normalize aliases
        op = instr.strip()

        # Arguments
        if op.startswith("ARG"):
            idx = int(op.replace("ARG", ""))
            state.int_stack.append(state.args[idx])
            return

        # Integer operations
        if op == "INT_ADD":
            b, a = state.int_stack.pop(), state.int_stack.pop()
            state.int_stack.append(f"(+ {a} {b})"); return
        if op == "INT_SUB":
            b, a = state.int_stack.pop(), state.int_stack.pop()
            state.int_stack.append(f"(- {a} {b})"); return
        if op == "INT_EQ":
            b, a = state.int_stack.pop(), state.int_stack.pop()
            state.bool_stack.append(f"(= {a} {b})"); return
        if op == "INT_LT":
            b, a = state.int_stack.pop(), state.int_stack.pop()
            state.bool_stack.append(f"(< {a} {b})"); return

        # Integer constants
        if op in ("INT.CONST.-1", "INT_CONST(-1)", "INT_CONST_m1"):
            state.int_stack.append("-1"); return
        if op in ("INT.CONST.0", "INT_CONST(0)", "INT_CONST_0"):
            state.int_stack.append("0"); return
        if op in ("INT.CONST.1", "INT_CONST(1)", "INT_CONST_1"):
            state.int_stack.append("1"); return

        # Bool ops
        if op == "BOOL_AND":
            b, a = state.bool_stack.pop(), state.bool_stack.pop()
            state.bool_stack.append(f"(and {a} {b})"); return
        if op == "BOOL_OR":
            b, a = state.bool_stack.pop(), state.bool_stack.pop()
            state.bool_stack.append(f"(or {a} {b})"); return
        if op == "BOOL_NOT":
            a = state.bool_stack.pop()
            state.bool_stack.append(f"(not {a})"); return

        # Bool consts
        if op in ("BOOL_CONST(True)", "BOOL.CONST.True", "BOOL_CONST_true"):
            state.bool_stack.append("true"); return
        if op in ("BOOL_CONST(False)", "BOOL.CONST.False", "BOOL_CONST_false"):
            state.bool_stack.append("false"); return

        # Data-structure helpers
        if op in ("DS.SIZE", "DS_SIZE"):
            state.int_stack.append(state.len_name); return

        if op in ("DS.GET.INDEX", "DS_GET_INDEX"):
            i = state.int_stack.pop() if state.int_stack else state.top_any()
            state.push_any(f"(select {state.arr_name} {i})"); return

        # Error marker (as a value)
        if op in ("ERR.PUSH", "ERR_PUSH"):
            state.push_any(error_val); return

        # Control: ITE — pops elseVal, thenVal, cond from the right stacks
        if op == "ITE":
            # cond from bool, then/else from int/any (use ANY view for generality)
            cond = state.bool_stack.pop() if state.bool_stack else state.top_any()
            then_val = state.top_any(); state.pop_any()
            else_val = state.top_any(); state.pop_any()
            # Push result into int stack by default (could be generalized)
            state.push_any(f"(ite {cond} {then_val} {else_val})"); return

        # Stack manipulation (ANY semantics: first qualifying stack)
        if op in ("DUP.ANY", "DUP_ANY"):
            state.dup_any(); return
        if op in ("POP.ANY", "POP_ANY"):
            state.pop_any(); return
        if op in ("SWAP.ANY", "SWAP_ANY"):
            state.swap_any(); return

        # If we reach here, unknown instruction
        raise ValueError(f"Unknown instruction: {op}")

    # Evaluate the top-level program
    eval_subprog(program)

    # Final SMT expression is the top from ANY view
    result = state.top_any()
    if result is None:
        # Empty result: conventionally return a neutral value
        result = "undef"
    return result


if __name__ == "__main__":
    # Example usage
    sample_program = [
        "ARG0",
        "INT_CONST_1",
        "INT_ADD",
        "DUP_ANY",
        "INT_CONST_0",
        "INT_LT",
        [
            "INT_CONST_42"
        ],
        "ITE"
    ]
    args = ["x"]
    smt_expr = translate_push_to_smt(sample_program, args)
    print("SMT Expression:")
    print(smt_expr)

    # Example 1: peekLast = select(arr, len-1)
    prog = ["DS.SIZE", "INT.CONST.1", "INT_SUB", "DS.GET.INDEX"]
    print(translate_push_to_smt(prog, args=["index"]))
    # => (select arr (- len 1))
    
    # Example 2: guarded peekLast using ITE
    prog2 = ["DS.SIZE", "INT.CONST.0", "INT_LT",  # len < 0 (nonsense, just illustration)
             ["DS.SIZE", "INT.CONST.1", "INT_SUB", "DS.GET.INDEX"],  # then
             "ERR.PUSH", "ITE"]
    print(translate_push_to_smt(prog2, args=["index"]))
    # => (ite (< len 0) (select arr (- len 1)) errorVal)
    
    # Example 3: nested with DUP.ANY and DS.GET.INDEX
    prog3 = [["BOOL.CONST.False", "DS.GET.INDEX"], "DUP.ANY", "DS.GET.INDEX"]
    print(translate_push_to_smt(prog3, args=["i"]))
    # Illustrative nested behavior; produces a composed select expression.
    
    # Example 4: ANY-manipulations
    prog4 = ["ARG0", "DUP.ANY", "SWAP.ANY", "INT_ADD"]
    print(translate_push_to_smt(prog4, args=["x"]))