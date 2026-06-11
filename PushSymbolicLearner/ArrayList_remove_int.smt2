; ============================================
; Method: remove#int
; Accuracy: 0.951377713044101
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for remove#int ---
(declare-const ds_remove_int (Array Int Int))
(declare-const ds_size_remove_int Int)
(declare-const input_int_0_remove_int Int)
(declare-const input_int_1_remove_int Int)
(declare-const input_str_0_remove_int String)
(declare-const input_bool_0_remove_int Bool)
(declare-const input_bool_1_remove_int Bool)
(declare-const output_int_remove_int Int)
(declare-const output_bool_remove_int Bool)
(declare-const output_str_remove_int String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_remove_int)

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
  ds_size_remove_int)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['DS.GET.INDEX', 'INT.CONST.0', ['DS.REMOVE.INDEX']] ---
; Step 0: DS.GET.INDEX => (select ds_remove_int 0)
; Step 1: INT.CONST.0 => 0
; Step 2: DS.REMOVE.INDEX => ; DS.REMOVE

; --- Verification Conditions ---
(assert (>= ds_size_remove_int 0))

(check-sat)
(get-model)