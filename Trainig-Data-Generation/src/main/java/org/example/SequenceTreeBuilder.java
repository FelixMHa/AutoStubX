package org.example;

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.*;

/**
 * Builds a sequence of state-changing method calls on a given class,
 * to prepare a valid internal state for symbolic training data generation.
 */
public class SequenceTreeBuilder {

    private final Class<?> clazz;
    private final Object baseObject;
    private final List<String> methodSequence;
    private final List<Method> appliedMutators;
    private static final List<String> mutatorPrefixes = List.of(
            "add", "put", "insert", "append", "push", "offer", "set", "remove", "clear");

    public SequenceTreeBuilder(Class<?> clazz) {
        this.clazz = clazz;
        this.methodSequence = new ArrayList<>();
        this.appliedMutators = new ArrayList<>();
        this.baseObject = createInstance(clazz);
    }

    public Object getBaseObject() {
        return baseObject;
    }

    public List<String> getSequence() {
        return methodSequence;
    }

    /**
     * Applies N random mutator methods to bring the object into a specific state.
     * @param steps Number of random mutators to apply
     */
    public void buildRandomState(int steps) {
        Method[] allMethods = clazz.getDeclaredMethods();

        for (int i = 0; i < steps; i++) {
            Method mutator = pickRandomMutator(allMethods);

            if (mutator == null) continue;

            try {
                Object[] args = RandomDataProvider.generateRandomArgs(mutator);
                mutator.setAccessible(true);
                mutator.invoke(baseObject, args);

                methodSequence.add(formatMethodCall(mutator, args));
                appliedMutators.add(mutator);

            } catch (Exception e) {
                // Skip silently, try next mutator
            }
        }
    }

    private Method pickRandomMutator(Method[] allMethods) {
        List<Method> candidates = Arrays.stream(allMethods)
                .filter(m -> Modifier.isPublic(m.getModifiers())
                        && !m.getName().equals("equals")
                        && m.getParameterCount() <= 2
                        && mutatorPrefixes.stream().anyMatch(p -> m.getName().startsWith(p)))
                .toList();

        if (candidates.isEmpty()) return null;

        return candidates.get(new Random().nextInt(candidates.size()));
    }

    private Object createInstance(Class<?> clazz) {
        try {
            return clazz.getDeclaredConstructor().newInstance();
        } catch (Exception e) {
            throw new RuntimeException("Cannot instantiate class: " + clazz.getName(), e);
        }
    }

    private String formatMethodCall(Method method, Object[] args) {
        StringBuilder sb = new StringBuilder();
        sb.append(method.getName()).append("(");
        for (int i = 0; i < args.length; i++) {
            sb.append("\"").append(String.valueOf(args[i])).append("\"");
            if (i < args.length - 1) sb.append(", ");
        }
        sb.append(")");
        return sb.toString();
    }

    /**
     * Applies the target method after building state and collects a training sample.
     *
     * @param targetMethod The method under test
     * @return SequenceInputOutputPair containing the mutation sequence, input/output, and types
     */
    public SequenceInputOutputPair<Object[], Object> applyTargetAndCollect(Method targetMethod) {
        try {
            Object[] targetArgs = RandomDataProvider.generateRandomArgs(targetMethod);
            targetMethod.setAccessible(true);
            Object output = targetMethod.invoke(baseObject, targetArgs);

            // Skip NaN/Infinite outputs
            if (output instanceof Double d && (Double.isNaN(d) || Double.isInfinite(d))) return null;
            if (output instanceof Float f && (Float.isNaN(f) || Float.isInfinite(f))) return null;

            // Form input array
            ArrayList<Object> fullInput = new ArrayList<>();
            fullInput.add(baseObject);
            fullInput.addAll(Arrays.asList(targetArgs));

            return new SequenceInputOutputPair<>(methodSequence, fullInput.toArray(), output);

        } catch (Exception e) {
            return null; // Silent fail
        }
    }
}
