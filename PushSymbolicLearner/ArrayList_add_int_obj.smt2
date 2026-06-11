; ============================================
; Method: add#int_obj
; Accuracy: 0.9885676741130092
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for add#int_obj ---
(declare-const ds_add_int_obj (Array Int Int))
(declare-const ds_size_add_int_obj Int)
(declare-const input_int_0_add_int_obj Int)
(declare-const input_int_1_add_int_obj Int)
(declare-const input_str_0_add_int_obj String)
(declare-const input_bool_0_add_int_obj Bool)
(declare-const input_bool_1_add_int_obj Bool)
(declare-const output_int_add_int_obj Int)
(declare-const output_bool_add_int_obj Bool)
(declare-const output_str_add_int_obj String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_add_int_obj)

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
  ds_size_add_int_obj)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['DS.INSERT.AT.INDEX', 'DS.LAST_INDEX_OF'] ---
; Step 0: DS.INSERT.AT.INDEX => ; DS.INSERT
; Step 1: DS.LAST_INDEX_OF => (ds.last_index_of ds_add_int_obj 0)

; --- Verification Conditions ---
(assert (>= ds_size_add_int_obj 0))

(check-sat)
(get-model)