; ============================================
; Method: lastIndexOf#obj
; Accuracy: 0.9875074620346238
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for lastIndexOf#obj ---
(declare-const ds_lastIndexOf_obj (Array Int Int))
(declare-const ds_size_lastIndexOf_obj Int)
(declare-const input_int_0_lastIndexOf_obj Int)
(declare-const input_int_1_lastIndexOf_obj Int)
(declare-const input_str_0_lastIndexOf_obj String)
(declare-const input_bool_0_lastIndexOf_obj Bool)
(declare-const input_bool_1_lastIndexOf_obj Bool)
(declare-const output_int_lastIndexOf_obj Int)
(declare-const output_bool_lastIndexOf_obj Bool)
(declare-const output_str_lastIndexOf_obj String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_lastIndexOf_obj)

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
  ds_size_lastIndexOf_obj)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['POP.ANY', 'INT.CONST.-1'] ---
; Step 0: POP.ANY => ; POP
; Step 1: INT.CONST.-1 => -1

; --- Verification Conditions ---
(assert (>= output_int_lastIndexOf_obj -1))

(check-sat)
(get-model)