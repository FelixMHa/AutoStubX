; ============================================
; Method: get#int
; Accuracy: 0.9527248104008668
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for get#int ---
(declare-const ds_get_int (Array Int Int))
(declare-const ds_size_get_int Int)
(declare-const input_int_0_get_int Int)
(declare-const input_int_1_get_int Int)
(declare-const input_str_0_get_int String)
(declare-const input_bool_0_get_int Bool)
(declare-const input_bool_1_get_int Bool)
(declare-const output_int_get_int Int)
(declare-const output_bool_get_int Bool)
(declare-const output_str_get_int String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_get_int)

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
  ds_size_get_int)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['BOOL.CONST.False', ['DS.GET.INDEX']] ---
; Step 0: BOOL.CONST.False => false
; Step 1: DS.GET.INDEX => (select ds_get_int 0)

; --- Verification Conditions ---
(assert (>= output_int_get_int -1))

(check-sat)
(get-model)