#!/usr/bin/env python3
"""
SMT-LIB Verification Script using Z3 Python API
"""

from z3 import *
import json
import sys
from pathlib import Path
import re


def verify_smt_file(smt_file: str, timeout: int = 30000) -> dict:
    """
    Verify an SMT-LIB file using Z3 Python API.
    """
    result = {
        'file': smt_file,
        'status': 'unknown',
        'model': None,
        'error': None,
        'time_ms': 0
    }
    
    try:
        # Create Z3 solver
        solver = Solver()
        solver.set('timeout', timeout)
        
        # Parse SMT file
        print(f"  Parsing: {smt_file}")
        solver.from_file(smt_file)
        
        # Check satisfiability
        import time
        start = time.time()
        status = solver.check()
        result['time_ms'] = int((time.time() - start) * 1000)
        
        if status == sat:
            result['status'] = 'sat'
            result['model'] = str(solver.model())
        elif status == unsat:
            result['status'] = 'unsat'
        else:
            result['status'] = 'unknown'
            
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


def verify_genome(genome_file: str, profile: str = 'ds_smt_minimal') -> dict:
    """Verify a PushGP genome by translating and checking."""
    from genome_to_smt import translate_genome_file
    
    smt_file = Path(genome_file).with_suffix('.smt2')
    translate_genome_file(genome_file, smt_file, profile, per_method=True)
    
    result = verify_smt_file(smt_file)
    result['genome'] = genome_file
    
    return result


def verify_all_methods(genome_file: str, profile: str = 'ds_smt_minimal'):
    """Verify each method in a genome separately"""
    from genome_to_smt import GenomeToSMTTranslator
    
    # Load genome
    with open(genome_file, 'r') as f:
        genome_data = json.load(f)
    
    translator = GenomeToSMTTranslator(profile=profile)
    
    results = []
    for method_name, method_data in genome_data.get('methods', {}).items():
        print(f"\n{'='*60}")
        print(f"Verifying: {method_name}")
        print(f"Accuracy: {method_data.get('accuracy', 'N/A')}")
        print(f"{'='*60}")
        
        # Create single-method SMT
        smt_content = translator._translate_single_method(method_name, method_data, genome_data)
        
        # Write to temp file
        safe_name = method_name.replace('#', '_').replace('.', '_')
        temp_file = f'temp_{safe_name}.smt2'
        with open(temp_file, 'w') as f:
            f.write(smt_content)
        
        print(f"  SMT file: {temp_file}")
        
        # Verify
        result = verify_smt_file(temp_file)
        result['method'] = method_name
        results.append(result)
        
        # Print result with details
        print(f"  Status: {result['status']}")
        print(f"  Time: {result['time_ms']}ms")
        
        if result['status'] == 'sat':
            print("  ✅ Method is VERIFIABLE")
        elif result['status'] == 'unsat':
            print("  ❌ Method has CONTRADICTIONS")
        elif result['status'] == 'error':
            print("  ❌ Verification ERROR")
            print(f"\n  Error Details:\n  {'-'*50}")
            error_msg = result['error']
            # Show error message
            print(f"  {error_msg[:500]}")
            print(f"  {'-'*50}")
            
            # Show the SMT file content for debugging
            print(f"\n  SMT File Content:\n  {'-'*50}")
            with open(temp_file, 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    print(f"  {i:3d}: {line.rstrip()}")
            print(f"  {'-'*50}")
        else:
            print("  ⚠️  Verification INCONCLUSIVE")
        
        # Cleanup
        Path(temp_file).unlink(missing_ok=True)
    
    # Summary
    print(f"\n{'='*60}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*60}")
    sat_count = sum(1 for r in results if r['status'] == 'sat')
    unsat_count = sum(1 for r in results if r['status'] == 'unsat')
    error_count = sum(1 for r in results if r['status'] == 'error')
    print(f"Total methods: {len(results)}")
    print(f"SAT (valid): {sat_count}")
    print(f"UNSAT (invalid): {unsat_count}")
    print(f"Errors: {error_count}")
    if len(results) > 0:
        print(f"Success rate: {sat_count/len(results)*100:.1f}%")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify SMT-LIB files with Z3')
    parser.add_argument('input', help='SMT file or genome JSON file')
    parser.add_argument('--genome', action='store_true', 
                       help='Input is a genome JSON (translate first)')
    parser.add_argument('--all-methods', action='store_true',
                       help='Verify each method separately')
    parser.add_argument('-t', '--timeout', type=int, default=30000,
                       help='Timeout in milliseconds')
    parser.add_argument('-p', '--profile', default='ds_smt_minimal',
                       help='Instruction profile')
    
    args = parser.parse_args()
    
    # Print Z3 version
    print(f"Z3 Version: {get_version_string()}")
    print()
    
    if args.all_methods and args.genome:
        verify_all_methods(args.input, args.profile)
    elif args.genome:
        result = verify_genome(args.input, profile=args.profile)
        print(f"\nVerification Result:")
        print(f"  Status: {result['status']}")
        print(f"  Time: {result['time_ms']}ms")
        if result['error']:
            print(f"  Error: {result['error']}")
    else:
        result = verify_smt_file(args.input, args.timeout)
        print(f"\nVerification Result:")
        print(f"  File: {result['file']}")
        print(f"  Status: {result['status']}")
        print(f"  Time: {result['time_ms']}ms")
        if result['status'] == 'sat':
            print(f"  ✅ SAT - Constraints are satisfiable")
        elif result['status'] == 'unsat':
            print(f"  ❌ UNSAT - Constraints are contradictory")
        if result['error']:
            print(f"  Error:\n{result['error']}")