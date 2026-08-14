package org.example;

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.*;

public class SequenceTreeBuilder {

    private final Object baseObject;
    private final Class<?> targetClass;
    private final List<List<String>> stepInputTypes;
    private final List<String> stepOutputTypes;
    private final List<String> sequence;
    private final List<Object> stepInputs;
    private final List<Object> stepOutputs;
    private final Random random = new Random();
    private final List<Method> validMethods;

    public SequenceTreeBuilder(Class<?> clazz) {
        this.targetClass = clazz;
        this.sequence = new ArrayList<>();
        this.stepInputs = new ArrayList<>();
        this.stepOutputs = new ArrayList<>();
        this.stepInputTypes = new ArrayList<>();
        this.stepOutputTypes = new ArrayList<>();
        this.baseObject = createInstance(clazz);
        this.validMethods = getValidMethods(clazz);
    }

    private Object createInstance(Class<?> clazz) {
        try {
            Object instance;

            if (clazz.isInterface() || Modifier.isAbstract(clazz.getModifiers())) {
                // Pick default concrete types for known interfaces
                if (Deque.class.isAssignableFrom(clazz))
                    instance = new ArrayDeque<>();
                else if (Queue.class.isAssignableFrom(clazz))
                    instance = new LinkedList<>();
                else if (List.class.isAssignableFrom(clazz))
                    instance = new ArrayList<>();
                else if (Set.class.isAssignableFrom(clazz))
                    instance = new HashSet<>();
                else if (Map.class.isAssignableFrom(clazz))
                    instance = new HashMap<>();
                else {
                    System.err.println("⚠️ No default implementation for " + clazz.getName());
                    return null;
                }
            } else {
                // Try no-arg constructor for concrete classes
                instance = clazz.getDeclaredConstructor().newInstance();
            }

            // ✅ 70% chance: pre-fill instance with 0–3 random elements
            if (instance instanceof Collection<?> && random.nextDouble() < 0.7) {
                int count = random.nextInt(4);
                @SuppressWarnings("unchecked")
                Collection<Object> coll = (Collection<Object>) instance;
                for (int i = 0; i < count; i++) {
                    Object randomElement = RandomDataProvider.randomPrimitiveOrString();
                    boolean out = coll.add(randomElement);
                    sequence.add("add#obj");
                    stepInputs.add(new Object[] { randomElement });
                    stepInputTypes.add(List.of("java.lang.Object"));
                    stepOutputs.add(out);
                    stepOutputTypes.add("boolean");
                }
                return coll;
            } else if (instance instanceof Map<?, ?> && random.nextDouble() < 0.7) {
                int count = random.nextInt(4);
                @SuppressWarnings("unchecked")
                Map<Object, Object> map = (Map<Object, Object>) instance;
                for (int i = 0; i < count; i++) {
                    Object randomKey = RandomDataProvider.randomPrimitiveOrString();
                    Object randomValue = RandomDataProvider.randomPrimitiveOrString();
                    Object out = map.put(randomKey, randomValue);
                    sequence.add("put#obj#obj");
                    stepInputs.add(new Object[] { randomKey, randomValue });
                    stepInputTypes.add(List.of(
                            "java.lang.Object",
                            "java.lang.Object"));
                    stepOutputs.add(out);
                    stepOutputTypes.add("java.lang.Object");
                }
                return map;
            }

            return instance;

        } catch (Exception e) {
            System.err.println("⚠️ Cannot instantiate " + clazz.getName() +
                    " (" + e.getClass().getSimpleName() + ")");
            return null;
        }
    }

    public SequenceInputOutputPair<Object[], Object> buildSequence(int steps) {
        if (baseObject == null)
            return null;

        while (sequence.size() < steps) {
            if (validMethods.isEmpty()) {
                return null;
            }

            Method candidate = validMethods.get(random.nextInt(validMethods.size()));

            Object[] args = RandomDataProvider.generateRandomArgs(candidate, baseObject);

            sequence.add(createMethodSignature(candidate));
            stepInputs.add(args);

            List<String> parameterTypes = Arrays.stream(candidate.getParameterTypes())
                    .map(Class::getTypeName)
                    .toList();
            stepInputTypes.add(parameterTypes);

            try {
                Object output = candidate.invoke(baseObject, args);
                stepOutputs.add(output);

                // This correctly records "void", Object for null results, etc.
                stepOutputTypes.add(candidate.getReturnType().getTypeName());
            } catch (Exception e) {
                stepOutputs.add("error");
                stepOutputTypes.add("error");
            }
        }
        return new SequenceInputOutputPair<>(
        sequence,
        stepInputs.toArray(),
        stepOutputs.toArray(),
        stepInputTypes,
        stepOutputTypes,
        createInitialState(),
        getDataStructureType(),
        targetClass.getName()
);
    }

    private String normalizeType(Class<?> type) {
        // Primitive types
        if (type == int.class)
            return "int";
        if (type == boolean.class)
            return "bool";
        if (type == float.class)
            return "float";
        if (type == double.class)
            return "float"; // Treat double as float
        if (type == long.class)
            return "long";
        if (type == byte.class)
            return "int"; // Small ints
        if (type == short.class)
            return "int"; // Small ints
        if (type == char.class)
            return "char";

        // Everything else is an object
        // This includes: Object, String, E (generic), T, K, V, Integer (boxed), etc.
        return "obj";
    }
    private String getDataStructureType() {
    if (baseObject instanceof Map<?, ?>) {
        return "map";
    }
    if (baseObject instanceof Set<?>) {
        return "set";
    }
    if (baseObject instanceof Collection<?>) {
        return "list";
    }
    return "generic";
}

private Map<String, Object> createInitialState() {
    String kind = getDataStructureType();

    Object data;
    if ("map".equals(kind)) {
        data = new LinkedHashMap<>();
    } else if ("list".equals(kind) || "set".equals(kind)) {
        data = new ArrayList<>();
    } else {
        data = null;
    }

    Map<String, Object> heapEntry = new LinkedHashMap<>();
    heapEntry.put("type", kind);
    heapEntry.put("data", data);
    heapEntry.put("fields", new LinkedHashMap<>());

    Map<String, Object> initialState = new LinkedHashMap<>();
    initialState.put("0", heapEntry);
    return initialState;
}

    private String createMethodSignature(Method method) {
    StringBuilder signature = new StringBuilder(method.getName());
    Class<?>[] parameterTypes = method.getParameterTypes();

    if (parameterTypes.length == 0) {
        return signature.append("#0").toString();
    }

    for (Class<?> parameterType : parameterTypes) {
        signature.append("#").append(normalizeType(parameterType));
    }

    return signature.toString();
}

    private List<Method> getValidMethods(Class<?> clazz) {
        List<String> disallowedReturnTypePrefixes = List.of(
                "java.util.Iterator",
                "java.util.ListIterator",
                "java.util.Enumeration",
                "java.util.Spliterator",
                "java.util.stream.Stream");
        List<String> problematicMethods = List.of(
                "removeIf",
                "replaceAll",
                "sort",
                "toArray",
                "subList",
                "copyOf",
                "forEach",
                "ensureCapacity",
                "trimToSize",
                "clone",
                "hashCode",
                "equals"

        );

        List<Method> candidates = Arrays.stream(clazz.getDeclaredMethods())
                // only public methods
                .filter(m -> Modifier.isPublic(m.getModifiers()))
                // skip forbidden return types by package prefix (e.g., java.util.Iterator,
                // Stream, etc.)
                .filter(m -> disallowedReturnTypePrefixes.stream()
                        .noneMatch(prefix -> m.getReturnType().getName().startsWith(prefix)))

                // only allow primitive or String return types
                .filter(m -> m.getReturnType().isPrimitive() || m.getReturnType().equals(String.class)
                        || m.getReturnType().equals(Object.class))

                // only allow methods whose *all parameters* are primitive or String
                .filter(m -> Arrays.stream(m.getParameterTypes())
                        .allMatch(pt -> pt.isPrimitive() || pt.equals(String.class) || pt.equals(Object.class)))

                // skip known problematic methods by name
                .filter(m -> !problematicMethods.contains(m.getName()))

                .toList();
        return candidates;
    }

}