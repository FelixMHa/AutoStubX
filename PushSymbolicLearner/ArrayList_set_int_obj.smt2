; ============================================
; Method: set#int_obj
; Accuracy: 0.9539317476993163
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for set#int_obj ---
(declare-const ds_set_int_obj (Array Int Int))
(declare-const ds_size_set_int_obj Int)
(declare-const input_int_0_set_int_obj Int)
(declare-const input_int_1_set_int_obj Int)
(declare-const input_str_0_set_int_obj String)
(declare-const input_bool_0_set_int_obj Bool)
(declare-const input_bool_1_set_int_obj Bool)
(declare-const output_int_set_int_obj Int)
(declare-const output_bool_set_int_obj Bool)
(declare-const output_str_set_int_obj String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_set_int_obj)

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
  ds_size_set_int_obj)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: [['BOOL.CONST.False', 'DS.GET.INDEX'], 'DUP.ANY', 'DS.GET.INDEX'] ---
; Step 0: BOOL.CONST.False => false
; Step 1: DS.GET.INDEX => (select ds_set_int_obj 0)
; Step 2: DUP.ANY => ; DUP
; Step 3: DS.GET.INDEX => (select ds_set_int_obj 0)

; --- Verification Conditions ---
(assert true)

(check-sat)
(get-model)