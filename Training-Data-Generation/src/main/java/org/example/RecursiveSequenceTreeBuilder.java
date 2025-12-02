package org.example;

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.*;
import java.util.stream.Stream;

public class RecursiveSequenceTreeBuilder {

    private final Class<?> clazz;
    private final Object baseObject;
    private final List<String> sequence;
    private final List<Object> stepInputs;
    private final List<Object> stepOutputs;
    private final Random random = new Random();

    public RecursiveSequenceTreeBuilder(Class<?> clazz) {
        this.clazz = clazz;
        this.sequence = new ArrayList<>();
        this.stepInputs = new ArrayList<>();
        this.stepOutputs = new ArrayList<>();
        this.baseObject = createInstance(clazz);
        
    }

    private Object createInstance(Class<?> clazz) {
    try {
        Object instance;

        if (clazz.isInterface() || Modifier.isAbstract(clazz.getModifiers())) {
            // Pick default concrete types for known interfaces
            if (Deque.class.isAssignableFrom(clazz)) instance = new ArrayDeque<>();
            else if (Queue.class.isAssignableFrom(clazz)) instance = new LinkedList<>();
            else if (List.class.isAssignableFrom(clazz)) instance = new ArrayList<>();
            else if (Set.class.isAssignableFrom(clazz)) instance = new HashSet<>();
            else if (Map.class.isAssignableFrom(clazz)) instance = new HashMap<>();
            else {
                System.err.println("⚠️ No default implementation for " + clazz.getName());
                return null;
            }
        } else {
            // Try no-arg constructor for concrete classes
            instance = clazz.getDeclaredConstructor().newInstance();
        }

        // ✅ 70% chance: pre-fill instance with 1–3 random elements
        if (instance instanceof Collection<?> && random.nextDouble() < 0.7) {
            int count = 1 + random.nextInt(3);
            Collection<Object>  coll = (Collection<Object>) instance;
            for (int i = 0; i < count; i++) {
                Object randomElement = RandomDataProvider.randomPrimitiveOrString();
                coll.add(randomElement);
                sequence.add("add");
                stepInputs.add(new Object[]{randomElement});
                stepOutputs.add(true);
            }
        return coll;
        } else if (instance instanceof Map<?, ?> && random.nextDouble() < 0.7) {
            int count = 1 + random.nextInt(3);
            Map<Object, Object> map = (Map<Object, Object>) instance;
            for (int i = 0; i < count; i++) {
                Object randomKey = RandomDataProvider.randomPrimitiveOrString();
                Object randomValue = RandomDataProvider.randomPrimitiveOrString();
                map.put(randomKey, randomValue);
                sequence.add("put");
                stepInputs.add(new Object[]{randomKey, randomValue});
                stepOutputs.add(null);
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
        if (baseObject == null) return null;

        Method[] methods = clazz.getMethods();

        while (sequence.size() < steps) {
            Method candidate = pickRandomMutator(methods);
            if (candidate == null) continue;

            try {
            
                Object[] args = RandomDataProvider.generateRandomArgs(candidate, baseObject);
                Object output = candidate.invoke(baseObject, args);

                sequence.add(candidate.getName());
                stepInputs.add(args);
                stepOutputs.add(output);

            } catch (Exception e) {
                // Skip bad calls
                return null;
            }
        }
        return new SequenceInputOutputPair<>(
                sequence,
                stepInputs.toArray(),
                stepOutputs.toArray()
        );
    }

    private Method pickRandomMutator(Method[] methods) {

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
                    "forEach"
                );


        List<Method> candidates = Arrays.stream(methods)
        // skip forbidden return types by package prefix (e.g., java.util.Iterator, Stream, etc.)
        .filter(m -> disallowedReturnTypePrefixes.stream()
                .noneMatch(prefix -> m.getReturnType().getName().startsWith(prefix)))

        // only allow primitive or String return types
        .filter(m -> m.getReturnType().isPrimitive() || m.getReturnType().equals(String.class) || m.getReturnType().equals(Object.class))

        // only allow methods whose *all parameters* are primitive or String
        .filter(m -> Arrays.stream(m.getParameterTypes())
                .allMatch(pt -> pt.isPrimitive() || pt.equals(String.class) || pt.equals(Object.class)))

        // skip known problematic methods by name
        .filter(m -> !problematicMethods.contains(m.getName()))

        .toList();


        if (candidates.isEmpty()) return null;
        return candidates.get(random.nextInt(candidates.size()));
    }
}