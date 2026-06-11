; ============================================
; Method: size#0
; Accuracy: 0.9810291998608742
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for size#0 ---
(declare-const ds_size_0 (Array Int Int))
(declare-const ds_size_size_0 Int)
(declare-const input_int_0_size_0 Int)
(declare-const input_int_1_size_0 Int)
(declare-const input_str_0_size_0 String)
(declare-const input_bool_0_size_0 Bool)
(declare-const input_bool_1_size_0 Bool)
(declare-const output_int_size_0 Int)
(declare-const output_bool_size_0 Bool)
(declare-const output_str_size_0 String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_size_0)

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
  ds_size_size_0)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: [['DS.SIZE']] ---
; Step 0: DS.SIZE => ds_size_size_0

; --- Verification Conditions ---
(assert (= output_int_size_0 ds_size_size_0))

(check-sat)
(get-model)