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

; ============================================
; Method: clear#0
; Accuracy: 0.9995912806539509
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for clear#0 ---
(declare-const ds_clear_0 (Array Int Int))
(declare-const ds_size_clear_0 Int)
(declare-const input_int_0_clear_0 Int)
(declare-const input_int_1_clear_0 Int)
(declare-const input_str_0_clear_0 String)
(declare-const input_bool_0_clear_0 Bool)
(declare-const input_bool_1_clear_0 Bool)
(declare-const output_int_clear_0 Int)
(declare-const output_bool_clear_0 Bool)
(declare-const output_str_clear_0 String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_clear_0)

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
  ds_size_clear_0)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['DS.CLEAR'] ---
; Step 0: DS.CLEAR => ; DS.CLEAR

; --- Verification Conditions ---
(assert (= ds_size_clear_0 0))

(check-sat)
(get-model)

; ============================================
; Method: isEmpty#0
; Accuracy: 0.9885891731553578
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for isEmpty#0 ---
(declare-const ds_isEmpty_0 (Array Int Int))
(declare-const ds_size_isEmpty_0 Int)
(declare-const input_int_0_isEmpty_0 Int)
(declare-const input_int_1_isEmpty_0 Int)
(declare-const input_str_0_isEmpty_0 String)
(declare-const input_bool_0_isEmpty_0 Bool)
(declare-const input_bool_1_isEmpty_0 Bool)
(declare-const output_int_isEmpty_0 Int)
(declare-const output_bool_isEmpty_0 Bool)
(declare-const output_str_isEmpty_0 String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_isEmpty_0)

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
  ds_size_isEmpty_0)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['DS.SIZE', 'INT.CONST.1', ['INT.LT']] ---
; Step 0: DS.SIZE => ds_size_isEmpty_0
; Step 1: INT.CONST.1 => 1
; Step 2: INT.LT => (<= 0 0)

; --- Verification Conditions ---
(assert (= output_bool_isEmpty_0 (= ds_size_isEmpty_0 0)))

(check-sat)
(get-model)

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

; ============================================
; Method: contains#obj
; Accuracy: 0.9942744271042985
; Fitness: 0.01859081200806984
; ============================================

(set-logic QF_SLIA)

; --- State Variables for contains#obj ---
(declare-const ds_contains_obj (Array Int Int))
(declare-const ds_size_contains_obj Int)
(declare-const input_int_0_contains_obj Int)
(declare-const input_int_1_contains_obj Int)
(declare-const input_str_0_contains_obj String)
(declare-const input_bool_0_contains_obj Bool)
(declare-const input_bool_1_contains_obj Bool)
(declare-const output_int_contains_obj Int)
(declare-const output_bool_contains_obj Bool)
(declare-const output_str_contains_obj String)

; --- Data Structure Axioms ---

; DS size function
(define-fun ds.size ((ds (Array Int Int))) Int
  ds_size_contains_obj)

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
  ds_size_contains_obj)

; Map contains_key function
(define-fun map.contains_key ((m (Array Int Int)) (key Int)) Bool
  true)


; --- Program: ['DS.LAST_INDEX_OF', 'BOOL.CONST.False', 'DS.GET.INDEX'] ---
; Step 0: DS.LAST_INDEX_OF => (ds.last_index_of ds_contains_obj 0)
; Step 1: BOOL.CONST.False => false
; Step 2: DS.GET.INDEX => (select ds_contains_obj 0)

; --- Verification Conditions ---
(assert (= output_bool_contains_obj (ds.contains ds_contains_obj input_int_0_contains_obj)))

(check-sat)
(get-model)

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