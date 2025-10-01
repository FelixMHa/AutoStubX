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
        this.baseObject = createInstance(clazz);
        this.sequence = new ArrayList<>();
        this.stepInputs = new ArrayList<>();
        this.stepOutputs = new ArrayList<>();
    }

    private Object createInstance(Class<?> clazz) {
        try {
            if (clazz.isInterface() || Modifier.isAbstract(clazz.getModifiers())) {
                // Order matters: test most specific first
                if (Deque.class.isAssignableFrom(clazz)) return new ArrayDeque<>();
                if (Queue.class.isAssignableFrom(clazz)) return new LinkedList<>();
                if (List.class.isAssignableFrom(clazz)) return new ArrayList<>();
                if (Set.class.isAssignableFrom(clazz)) return new HashSet<>();
                if (Map.class.isAssignableFrom(clazz)) return new HashMap<>();

                System.err.println("⚠️ No default implementation for " + clazz.getName());
                return null;
            }

            // Default: try to call a public no-arg constructor
            return clazz.getDeclaredConstructor().newInstance();

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
                Object[] args = RandomDataProvider.generateRandomArgs(candidate);
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
                    "copyOf"
                );


        List<Method> candidates = Arrays.stream(methods)
                // skip iterator-like methods
                .filter(m -> disallowedReturnTypePrefixes.stream().noneMatch(m.getReturnType().getName()::startsWith))
                .filter(m -> !problematicMethods.contains(m.getName()))
                .toList();

        if (candidates.isEmpty()) return null;
        return candidates.get(random.nextInt(candidates.size()));
    }
}
