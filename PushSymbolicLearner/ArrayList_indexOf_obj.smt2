; ============================================
; Method: indexOf#obj
; Accuracy: 0.9833836000955565
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for indexOf#obj ---
(declare-const ds_indexOf_obj (Array Int Int))
(declare-const ds_size_indexOf_obj Int)
(declare-const input_int_0_indexOf_obj Int)
(declare-const input_int_1_indexOf_obj Int)
(declare-const input_str_0_indexOf_obj String)
(declare-const input_bool_0_indexOf_obj Bool)
(declare-const input_bool_1_indexOf_obj Bool)
(declare-const output_int_indexOf_obj Int)
(declare-const output_bool_indexOf_obj Bool)
(declare-const output_str_indexOf_obj String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_indexOf_obj)

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
  ds_size_indexOf_obj)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['DS.INDEX_OF'] ---
; Step 0: DS.INDEX_OF => (ds.index_of ds_indexOf_obj 0)

; --- Verification Conditions ---
(assert (>= output_int_indexOf_obj -1))

(check-sat)
(get-model)