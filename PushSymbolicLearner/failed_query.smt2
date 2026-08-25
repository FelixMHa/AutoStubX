(set-logic ALL)
(set-option :produce-models true)

; Boxed Java values used by receiver payloads and collection/map contents.
(declare-datatypes () ((JValue
  (JNull)
  (JInt (j-int Int))
  (JBool (j-bool Bool))
  (JReal (j-real Real))
  (JString (j-string String))
  (JRef (j-ref Int)))))

(declare-datatypes () ((ObjectKind (K_NONE) (K_LIST) (K_MAP) (K_SET) (K_OBJECT))))
(declare-datatypes () ((OutcomeKind (OUT_NORMAL) (OUT_THROWN) (OUT_MISSING))))
(declare-datatypes () ((ExceptionKind
  (EX_NONE)
  (EX_INVALID_RECEIVER)
  (EX_INVALID_ARGUMENT)
  (EX_INDEX_OUT_OF_BOUNDS)
  (EX_EMPTY_DATA_STRUCTURE)
  (EX_ARITHMETIC)
  (EX_MODELLED)
  (EX_STEP_LIMIT)
  (EX_INTERNAL))))

; One symbolic heap supports multiple object references and aliasing.
(declare-datatypes () ((Heap
  (mk-heap
    (heap-kind (Array Int ObjectKind))
    (heap-object-value (Array Int JValue))
    (heap-list-size (Array Int Int))
    (heap-list-data (Array Int (Array Int JValue)))
    (heap-map-size (Array Int Int))
    (heap-map-present (Array Int (Array JValue Bool)))
    (heap-map-data (Array Int (Array JValue JValue)))
    (heap-set-size (Array Int Int))
    (heap-set-present (Array Int (Array JValue Bool)))))))

(declare-datatypes () ((StubResult
  (mk-result
    (result-heap Heap)
    (result-outcome OutcomeKind)
    (result-value JValue)
    (result-exception ExceptionKind)))))

; Java integer arithmetic helpers (division truncates toward zero).
(define-fun java-abs ((value Int)) Int (ite (< value 0) (- value) value))
(define-fun java-div ((left Int) (right Int)) Int
  (let ((quotient (div (java-abs left) (java-abs right))))
    (ite (= (< left 0) (< right 0)) quotient (- quotient))))
(define-fun java-rem ((left Int) (right Int)) Int
  (- left (* right (java-div left right))))

; Executable list-array transformations and searches.
;
; These helpers deliberately avoid global forall axioms.  list-insert and
; list-remove are array-valued lambda expressions, so selecting an element
; reduces directly to an ite/select term.  indexOf/lastIndexOf use recursive
; searches that unfold only when a query actually calls them.  This keeps
; unrelated stubs (size/isEmpty/get/etc.) in a quantifier-free solver context.
(define-fun list-insert
  ((data (Array Int JValue)) (size Int) (index Int) (value JValue))
  (Array Int JValue)
  (lambda ((position Int))
    (ite (and (<= 0 position) (< position (+ size 1)))
         (ite (< position index)
              (select data position)
              (ite (= position index) value (select data (- position 1))))
         (select data position))))

(define-fun list-remove
  ((data (Array Int JValue)) (size Int) (index Int))
  (Array Int JValue)
  (lambda ((position Int))
    (ite (and (<= 0 position) (< position (- size 1)))
         (ite (< position index)
              (select data position)
              (select data (+ position 1)))
         (select data position))))

; Exact first-match search.  For concrete sizes this unfolds to a finite
; chain of select/equality tests; symbolic unbounded sizes retain recursion
; only in queries that actually use indexOf/contains/remove-by-value.
(define-fun-rec list-index-of-from
  ((data (Array Int JValue)) (size Int) (value JValue) (position Int)) Int
  (ite (>= position size)
       (- 1)
       (ite (= (select data position) value)
            position
            (list-index-of-from data size value (+ position 1)))))

(define-fun list-index-of
  ((data (Array Int JValue)) (size Int) (value JValue)) Int
  (ite (<= size 0)
       (- 1)
       (list-index-of-from data size value 0)))

; Exact last-match search, scanning from size-1 toward zero.
(define-fun-rec list-last-index-of-from
  ((data (Array Int JValue)) (value JValue) (position Int)) Int
  (ite (< position 0)
       (- 1)
       (ite (= (select data position) value)
            position
            (list-last-index-of-from data value (- position 1)))))

(define-fun list-last-index-of
  ((data (Array Int JValue)) (size Int) (value JValue)) Int
  (ite (<= size 0)
       (- 1)
       (list-last-index-of-from data value (- size 1))))

(define-fun list-contains ((data (Array Int JValue)) (size Int) (value JValue)) Bool
  (<= 0 (list-index-of data size value)))

; Constructors useful when asserting or composing generated stubs.
(define-fun empty-heap () Heap
  (mk-heap
    ((as const (Array Int ObjectKind)) K_NONE)
    ((as const (Array Int JValue)) JNull)
    ((as const (Array Int Int)) 0)
    ((as const (Array Int (Array Int JValue))) ((as const (Array Int JValue)) JNull))
    ((as const (Array Int Int)) 0)
    ((as const (Array Int (Array JValue Bool))) ((as const (Array JValue Bool)) false))
    ((as const (Array Int (Array JValue JValue))) ((as const (Array JValue JValue)) JNull))
    ((as const (Array Int Int)) 0)
    ((as const (Array Int (Array JValue Bool))) ((as const (Array JValue Bool)) false))))

(define-fun heap-new-object ((heap Heap) (reference Int) (value JValue)) Heap
  (mk-heap
    (store (heap-kind heap) reference K_OBJECT)
    (store (heap-object-value heap) reference value)
    (heap-list-size heap)
    (heap-list-data heap)
    (heap-map-size heap)
    (heap-map-present heap)
    (heap-map-data heap)
    (heap-set-size heap)
    (heap-set-present heap)))

(define-fun heap-new-list ((heap Heap) (reference Int)) Heap
  (mk-heap
    (store (heap-kind heap) reference K_LIST)
    (heap-object-value heap)
    (store (heap-list-size heap) reference 0)
    (store (heap-list-data heap) reference ((as const (Array Int JValue)) JNull))
    (heap-map-size heap)
    (heap-map-present heap)
    (heap-map-data heap)
    (heap-set-size heap)
    (heap-set-present heap)))

(define-fun heap-new-map ((heap Heap) (reference Int)) Heap
  (mk-heap
    (store (heap-kind heap) reference K_MAP)
    (heap-object-value heap)
    (heap-list-size heap)
    (heap-list-data heap)
    (store (heap-map-size heap) reference 0)
    (store (heap-map-present heap) reference ((as const (Array JValue Bool)) false))
    (store (heap-map-data heap) reference ((as const (Array JValue JValue)) JNull))
    (heap-set-size heap)
    (heap-set-present heap)))

(define-fun heap-new-set ((heap Heap) (reference Int)) Heap
  (mk-heap
    (store (heap-kind heap) reference K_SET)
    (heap-object-value heap)
    (heap-list-size heap)
    (heap-list-data heap)
    (heap-map-size heap)
    (heap-map-present heap)
    (heap-map-data heap)
    (store (heap-set-size heap) reference 0)
    (store (heap-set-present heap) reference ((as const (Array JValue Bool)) false))))
; Java/trace method: java.lang.Boolean.booleanValue#0
; Receiver kind: generic
; Argument types: []
; Return type: boolean
; Symbolic paths: 1
(define-fun stub_booleanValue_0_pre ((pre Heap) (receiver Int)) Bool
  (and (<= 0 receiver) ((_ is JBool) (select (heap-object-value pre) receiver))))
(define-fun stub_booleanValue_0 ((pre Heap) (receiver Int)) StubResult
  (ite (and (<= 0 receiver) ((_ is JBool) (select (heap-object-value pre) receiver))) (mk-result (mk-heap (heap-kind pre) (heap-object-value pre) (heap-list-size pre) (heap-list-data pre) (heap-map-size pre) (heap-map-present pre) (heap-map-data pre) (heap-set-size pre) (heap-set-present pre)) OUT_NORMAL (JBool (j-bool (select (heap-object-value pre) receiver))) EX_NONE) (mk-result pre OUT_THROWN JNull EX_INVALID_RECEIVER)))

(define-fun h_init_0 () Heap empty-heap)
(define-fun h_init_1 () Heap (mk-heap (store (heap-kind h_init_0) 0 K_OBJECT) (heap-list-size h_init_0) (heap-list-data h_init_0) (heap-map-size h_init_0) (heap-map-present h_init_0) (heap-map-data h_init_0) (heap-set-size h_init_0) (heap-set-present h_init_0)))
(define-fun h0 () Heap h_init_1)
(define-fun r0 () StubResult (stub_booleanValue_0 h0 0))
(push 1)
(assert (not (and (= (result-outcome r0) OUT_NORMAL) (= (result-exception r0) EX_NONE) (= (result-value r0) (JBool false)))))
(check-sat)
(pop 1)