; ============================================
; Method: remove#obj
; Accuracy: 0.9800408115671642
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for remove#obj ---
(declare-const ds_remove_obj (Array Int Int))
(declare-const ds_size_remove_obj Int)
(declare-const input_int_0_remove_obj Int)
(declare-const input_int_1_remove_obj Int)
(declare-const input_str_0_remove_obj String)
(declare-const input_bool_0_remove_obj Bool)
(declare-const input_bool_1_remove_obj Bool)
(declare-const output_int_remove_obj Int)
(declare-const output_bool_remove_obj Bool)
(declare-const output_str_remove_obj String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_remove_obj)

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
  ds_size_remove_obj)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['DS.LAST_INDEX_OF', 'BOOL.CONST.False', 'DS.REMOVE.INDEX'] ---
; Step 0: DS.LAST_INDEX_OF => (ds.last_index_of ds_remove_obj 0)
; Step 1: BOOL.CONST.False => false
; Step 2: DS.REMOVE.INDEX => ; DS.REMOVE

; --- Verification Conditions ---
(assert (>= ds_size_remove_obj 0))

(check-sat)
(get-model)