from typing import List, Any, Optional, Dict

class TrainingExample:
    """Training example with method sequence and expected output"""
    def __init__(
        self,
        sequence: List[str],
        input_args: List[List[Any]],
        expected_outputs: List[Any],
        type_inputs: List[List[str]],
        type_outputs: List[str],
        data_structure_type: str,
        initial_state: Optional[Dict[int, Any]] = None  # NEW: ref_id -> data
    ):
        self.sequence = sequence
        self.input_args = input_args
        self.expected_outputs = expected_outputs
        self.type_inputs = type_inputs
        self.type_outputs = type_outputs
        self.data_structure_type = data_structure_type
        self.initial_state = initial_state or {}  # Default: empty