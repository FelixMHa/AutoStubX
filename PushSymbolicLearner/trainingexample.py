from typing import List, Any
class TrainingExample:
    """Training example with method sequence and expected output"""
    sequence: List[str]
    input_args: List[List[Any]]
    expected_outputs: List[Any]
    type_inputs: List[List[str]]
    type_outputs: List[str]
    data_structure_type: str