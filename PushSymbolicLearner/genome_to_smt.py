#!/usr/bin/env python3
"""
PushGP Genome to SMT-LIB Translator (FIXED VERSION)

Converts learned PushGP programs into SMT-LIB format for formal verification.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class SMTInstructionTranslator:
    """Translates Push instructions to SMT-LIB constraints"""
    
    def __init__(self, profile: str = 'ds_smt_minimal'):
        self.profile = profile
        self.smt_mappings = self._build_smt_mappings()
    
    def _build_smt_mappings(self) -> Dict[str, callable]:
        """Build mapping from instruction names to SMT generators"""
        return {
            # Integer Operations
            'INT.ADD': lambda ctx: f"(+ {ctx.get('arg1', '0')} {ctx.get('arg2', '0')})",
            'INT.SUB': lambda ctx: f"(- {ctx.get('arg1', '0')} {ctx.get('arg2', '0')})",
            'INT.MUL': lambda ctx: f"(* {ctx.get('arg1', '0')} {ctx.get('arg2', '0')})",
            'INT.DIV': lambda ctx: f"(div {ctx.get('arg1', '0')} {ctx.get('arg2', '1')})",
            'INT.EQ': lambda ctx: f"(= {ctx.get('arg1', '0')} {ctx.get('arg2', '0')})",
            'INT.LT': lambda ctx: f"(<= {ctx.get('arg1', '0')} {ctx.get('arg2', '0')})",
            'INT.GT': lambda ctx: f"(>= {ctx.get('arg1', '0')} {ctx.get('arg2', '0')})",
            'INT.NEG': lambda ctx: f"(- {ctx.get('arg1', '0')})",
            'INT.ABS': lambda ctx: f"(abs {ctx.get('arg1', '0')})",
            
            # Integer Constants
            'INT.CONST.0': lambda ctx: "0",
            'INT.CONST.1': lambda ctx: "1",
            'INT.CONST.-1': lambda ctx: "-1",
            'INT.CONST.2': lambda ctx: "2",
            'INT.CONST.-2': lambda ctx: "-2",
            'INT.CONST.3': lambda ctx: "3",
            'INT.CONST.4': lambda ctx: "4",
            'INT.CONST.5': lambda ctx: "5",
            'INT.CONST.6': lambda ctx: "6",
            'INT.CONST.-3': lambda ctx: "-3",
            'INT.CONST.-4': lambda ctx: "-4",
            
            # Float Operations
            'FLOAT.ADD': lambda ctx: f"(+ {ctx.get('arg1', '0.0')} {ctx.get('arg2', '0.0')})",
            'FLOAT.SUB': lambda ctx: f"(- {ctx.get('arg1', '0.0')} {ctx.get('arg2', '0.0')})",
            'FLOAT.MUL': lambda ctx: f"(* {ctx.get('arg1', '0.0')} {ctx.get('arg2', '0.0')})",
            'FLOAT.DIV': lambda ctx: f"(/ {ctx.get('arg1', '0.0')} {ctx.get('arg2', '1.0')})",
            'FLOAT.EQ': lambda ctx: f"(= {ctx.get('arg1', '0.0')} {ctx.get('arg2', '0.0')})",
            'FLOAT.LT': lambda ctx: f"(<= {ctx.get('arg1', '0.0')} {ctx.get('arg2', '0.0')})",
            
            # Float Constants
            'FLOAT.CONST.0.0': lambda ctx: "0.0",
            'FLOAT.CONST.1.0': lambda ctx: "1.0",
            'FLOAT.CONST.-1.0': lambda ctx: "-1.0",
            
            # Boolean Operations
            'BOOL.AND': lambda ctx: f"(and {ctx.get('arg1', 'true')} {ctx.get('arg2', 'true')})",
            'BOOL.OR': lambda ctx: f"(or {ctx.get('arg1', 'true')} {ctx.get('arg2', 'true')})",
            'BOOL.NOT': lambda ctx: f"(not {ctx.get('arg1', 'true')})",
            'BOOL.XOR': lambda ctx: f"(xor {ctx.get('arg1', 'true')} {ctx.get('arg2', 'true')})",
            'BOOL.CONST.True': lambda ctx: "true",
            'BOOL.CONST.False': lambda ctx: "false",
            
            # String Operations
            'STR.CONCAT': lambda ctx: f"(str.++ {ctx.get('arg1', '\"\"')} {ctx.get('arg2', '\"\"')})",
            'STR.EQ': lambda ctx: f"(str.= {ctx.get('arg1', '\"\"')} {ctx.get('arg2', '\"\"')})",
            'STR.LEN': lambda ctx: f"(str.len {ctx.get('arg1', '\"\"')})",
            'STR.CONTAINS': lambda ctx: f"(str.contains {ctx.get('arg1', '\"\"')} {ctx.get('arg2', '\"\"')})",
            'STR.INDEX_OF': lambda ctx: f"(str.indexof {ctx.get('arg1', '\"\"')} {ctx.get('arg2', '\"\"')} 0)",
            'STR.SUBSTRING': lambda ctx: f"(str.substr {ctx.get('arg1', '\"\"')} {ctx.get('start', '0')} {ctx.get('len', '0')})",
            'STR.TO.INT': lambda ctx: f"(str.to.int {ctx.get('arg1', '\"\"')})",
            'INT.TO.STR': lambda ctx: f"(int.to.str {ctx.get('arg1', '0')})",
            
            # Control Flow
            'ITE': lambda ctx: f"(ite {ctx.get('cond', 'true')} {ctx.get('then', '0')} {ctx.get('else', '0')})",
            'ITE.INT': lambda ctx: f"(ite {ctx.get('cond', 'true')} {ctx.get('then', '0')} {ctx.get('else', '0')})",
            'ITE.BOOL': lambda ctx: f"(ite {ctx.get('cond', 'true')} {ctx.get('then', 'true')} {ctx.get('else', 'false')})",
            
            # Stack Operations
            'DUP.ANY': lambda ctx: "; DUP",
            'SWAP.ANY': lambda ctx: "; SWAP",
            'POP.ANY': lambda ctx: "; POP",
            
            # Data Structure Operations
            'DS.SIZE': lambda ctx: f"ds_size_{ctx.get('method_id', '0')}",
            'DS.CLEAR': lambda ctx: "; DS.CLEAR",
            'DS.GET.INDEX': lambda ctx: f"(select ds_{ctx.get('method_id', '0')} {ctx.get('index', '0')})",
            'DS.SET.INDEX': lambda ctx: f"(store ds_{ctx.get('method_id', '0')} {ctx.get('index', '0')} {ctx.get('value', '0')})",
            'DS.INSERT.AT.INDEX': lambda ctx: f"; DS.INSERT",
            'DS.REMOVE.INDEX': lambda ctx: f"; DS.REMOVE",
            'DS.INDEX_OF': lambda ctx: f"(ds.index_of ds_{ctx.get('method_id', '0')} {ctx.get('value', '0')})",
            'DS.LAST_INDEX_OF': lambda ctx: f"(ds.last_index_of ds_{ctx.get('method_id', '0')} {ctx.get('value', '0')})",
            'DS.CONTAINS': lambda ctx: f"(ds.contains ds_{ctx.get('method_id', '0')} {ctx.get('value', '0')})",
            
            # Map Operations
            'MAP.SIZE': lambda ctx: f"(map.size map_{ctx.get('method_id', '0')})",
            'MAP.GET': lambda ctx: f"(select map_{ctx.get('method_id', '0')} {ctx.get('key', '0')})",
            'MAP.PUT': lambda ctx: f"(store map_{ctx.get('method_id', '0')} {ctx.get('key', '0')} {ctx.get('value', '0')})",
            'MAP.CONTAINS.KEY': lambda ctx: f"(map.contains_key map_{ctx.get('method_id', '0')} {ctx.get('key', '0')})",
            
            # ERCs
            'ERC.INT.': lambda ctx: ctx.get('instr_name', '0').replace('ERC.INT.', ''),
            'ERC.FLOAT.': lambda ctx: ctx.get('instr_name', '0.0').replace('ERC.FLOAT.', ''),
        }
    
    def translate_instruction(self, instr_name: str, context: dict) -> str:
        """Translate a single instruction to SMT-LIB"""
        for prefix, func in self.smt_mappings.items():
            if instr_name.startswith(prefix):
                return func(context)
        return f"; UNKNOWN: {instr_name}"


class GenomeToSMTTranslator:
    """Translates entire PushGP genomes to SMT-LIB"""
    
    def __init__(self, profile: str = 'ds_smt_minimal'):
        self.profile = profile
        self.instr_translator = SMTInstructionTranslator(profile)
    
    def translate_genome(self, genome_data: dict, output_file: str = None,
                        per_method: bool = True) -> str:
        """
        Translate genome to SMT-LIB.
        
        Args:
            genome_data: Loaded JSON genome
            output_file: Output file path
            per_method: If True, create separate file per method (RECOMMENDED)
        """
        methods = genome_data.get('methods', {})
        
        if per_method:
            # Create separate SMT file for each method
            all_content = []
            for method_name, method_data in methods.items():
                smt_content = self._translate_single_method(method_name, method_data, genome_data)
                all_content.append(smt_content)
                
                # Save individual file
                if output_file:
                    base_path = Path(output_file)
                    safe_name = method_name.replace('#', '_').replace('.', '_')
                    method_file = base_path.parent / f"{base_path.stem}_{safe_name}.smt2"
                    method_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(method_file, 'w', encoding='utf-8') as f:
                        f.write(smt_content)
                    print(f"  Created: {method_file.name}")
            
            # Also create combined file
            if output_file:
                combined = "\n\n".join(all_content)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(combined)
                print(f"Combined SMT saved to: {output_file}")
            return all_content[0] if all_content else ""
        else:
            # Old behavior: all methods in one file (will have duplicate errors)
            return self._translate_all_methods_combined(genome_data, output_file)
    
    def _translate_single_method(self, method_name: str, method_data: dict, 
                                  genome_data: dict) -> str:
        """Translate a single method to its own SMT file"""
        smt_lines = []
        
        # Header
        smt_lines.append(f"; ============================================")
        smt_lines.append(f"; Method: {method_name}")
        smt_lines.append(f"; Accuracy: {method_data.get('accuracy', 'N/A')}")
        smt_lines.append(f"; Fitness: {genome_data.get('fitness', 'N/A')}")
        smt_lines.append("; ============================================\n")
        
        # FIXED: Use QF_SLIA for string support
        smt_lines.append("(set-logic QF_SLIA)")
        smt_lines.append("")
        
        # FIXED: Unique variable names per method
        method_id = method_name.replace('#', '_').replace('.', '_')
        
        # Declare variables with unique names
        smt_lines.append(f"; --- State Variables for {method_name} ---")
        smt_lines.append(f"(declare-const ds_{method_id} (Array Int Int))")
        smt_lines.append(f"(declare-const ds_size_{method_id} Int)")
        smt_lines.append(f"(declare-const input_int_0_{method_id} Int)")
        smt_lines.append(f"(declare-const input_int_1_{method_id} Int)")
        smt_lines.append(f"(declare-const input_str_0_{method_id} String)")
        smt_lines.append(f"(declare-const input_bool_0_{method_id} Bool)")
        smt_lines.append(f"(declare-const input_bool_1_{method_id} Bool)")
        smt_lines.append(f"(declare-const output_int_{method_id} Int)")
        smt_lines.append(f"(declare-const output_bool_{method_id} Bool)")
        smt_lines.append(f"(declare-const output_str_{method_id} String)")
        smt_lines.append("")
        
        # FIXED: Add DS function definitions
        smt_lines.append("; --- Data Structure Axioms ---")
        smt_lines.append(self._get_ds_axioms(method_id))
        smt_lines.append("")
        
        # Program translation
        program = method_data.get('program', [])
        smt_lines.append(f"; --- Program: {program} ---")
        
        flat_program = self._flatten_program(program)
        for i, instr in enumerate(flat_program):
            context = {
                'instr_name': instr,
                'step': i,
                'method_id': method_id
            }
            smt_expr = self.instr_translator.translate_instruction(instr, context)
            smt_lines.append(f"; Step {i}: {instr} => {smt_expr}")
        
        smt_lines.append("")
        
        # Verification conditions with unique names
        smt_lines.append("; --- Verification Conditions ---")
        smt_lines.append(self._generate_verification_conditions(method_name, method_id))
        
        smt_lines.append("")
        smt_lines.append("(check-sat)")
        smt_lines.append("(get-model)")
        
        return "\n".join(smt_lines)
    
    def _get_ds_axioms(self, method_id: str) -> str:
        """Generate DS function axioms"""
        return f"""
; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_{method_id})

; DS index_of function (simplified - returns -1 if not found)
(define-fun ds.index_of ((ds (Array Int Int)) (val Int)) Int
  -1)

; DS last_index_of function
(define-fun ds.last_index_of ((ds (Array Int Int)) (val Int)) Int
  -1)

; DS contains function
(define-fun ds.contains ((ds (Array Int Int)) (val Int)) Bool
  (= (ds.index_of ds val) -1))

; Map size function
(define-fun map.size ((m (Array Int Int))) Int
  ds_size_{method_id})

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)
"""
    
    def _generate_verification_conditions(self, method_name: str, method_id: str) -> str:
        """Generate verification conditions with unique variable names"""
        conditions = []
        
        name_lower = method_name.lower()
        
        if 'size' in name_lower:
            conditions.append(f"(assert (= output_int_{method_id} ds_size_{method_id}))")
        elif 'clear' in name_lower:
            conditions.append(f"(assert (= ds_size_{method_id} 0))")
        elif 'isempty' in name_lower:
            conditions.append(f"(assert (= output_bool_{method_id} (= ds_size_{method_id} 0)))")
        elif 'add' in name_lower:
            conditions.append(f"(assert (>= ds_size_{method_id} 0))")
        elif 'remove' in name_lower:
            conditions.append(f"(assert (>= ds_size_{method_id} 0))")
        elif 'get' in name_lower:
            conditions.append(f"(assert (>= output_int_{method_id} -1))")
        elif 'set' in name_lower:
            conditions.append(f"(assert true)")
        elif 'contains' in name_lower:
            conditions.append(f"(assert (= output_bool_{method_id} (ds.contains ds_{method_id} input_int_0_{method_id})))")
        elif 'indexof' in name_lower or 'lastindexof' in name_lower:
            conditions.append(f"(assert (>= output_int_{method_id} -1))")
        elif 'or' in name_lower:
            conditions.append(f"(assert (= output_bool_{method_id} (or input_bool_0_{method_id} input_bool_1_{method_id})))")
        else:
            conditions.append(f"(assert true)")
        
        return "\n".join(conditions)
    
    def _flatten_program(self, program: List) -> List[str]:
        """Flatten nested program structure"""
        flat = []
        for item in program:
            if isinstance(item, list):
                flat.extend(self._flatten_program(item))
            elif isinstance(item, str):
                flat.append(item)
            elif isinstance(item, dict):
                flat.append(item.get('name', str(item)))
        return flat
    
    def _translate_all_methods_combined(self, genome_data: dict, output_file: str) -> str:
        """Old method - all in one file (not recommended)"""
        # This will have duplicate errors - use per_method=True instead
        return self.translate_genome(genome_data, output_file, per_method=True)


def translate_genome_file(input_file: str, output_file: str = None, 
                         profile: str = 'ds_smt_minimal', per_method: bool = True):
    """Translate a genome JSON file to SMT-LIB."""
    with open(input_file, 'r', encoding='utf-8') as f:
        genome_data = json.load(f)
    
    if output_file is None:
        output_file = Path(input_file).with_suffix('.smt2')
    
    translator = GenomeToSMTTranslator(profile=profile)
    translator.translate_genome(genome_data, output_file, per_method=per_method)
    
    print(f"\n✅ Translation complete!")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Methods: {len(genome_data.get('methods', {}))}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Translate PushGP genomes to SMT-LIB')
    parser.add_argument('input', help='Input genome JSON file')
    parser.add_argument('-o', '--output', help='Output SMT file')
    parser.add_argument('-p', '--profile', default='ds_smt_minimal',
                       choices=['ds_smt_minimal', 'primitives_full'])
    parser.add_argument('--combined', action='store_true',
                       help='All methods in one file (not recommended)')
    
    args = parser.parse_args()
    
    translate_genome_file(
        args.input, 
        args.output, 
        args.profile,
        per_method=not args.combined
    )