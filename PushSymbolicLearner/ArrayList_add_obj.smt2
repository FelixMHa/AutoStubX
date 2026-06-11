; ============================================
; Method: add#obj
; Accuracy: 0.9907590759075907
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for add#obj ---
(declare-const ds_add_obj (Array Int Int))
(declare-const ds_size_add_obj Int)
(declare-const input_int_0_add_obj Int)
(declare-const input_int_1_add_obj Int)
(declare-const input_str_0_add_obj String)
(declare-const input_bool_0_add_obj Bool)
(declare-const input_bool_1_add_obj Bool)
(declare-const output_int_add_obj Int)
(declare-const output_bool_add_obj Bool)
(declare-const output_str_add_obj String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_add_obj)

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
  ds_size_add_obj)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['DS.SIZE', 'DS.INSERT.AT.INDEX', 'BOOL.CONST.False', 'BOOL.CONST.True'] ---
; Step 0: DS.SIZE => ds_size_add_obj
; Step 1: DS.INSERT.AT.INDEX => ; DS.INSERT
; Step 2: BOOL.CONST.False => false
; Step 3: BOOL.CONST.True => true

; --- Verification Conditions ---
(assert (>= ds_size_add_obj 0))

(check-sat)
(get-model)