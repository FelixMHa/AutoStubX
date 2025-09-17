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
    private final List<Object[]> stepInputs;
    private final List<Object> stepOutputs;
    private static final List<String> mutatorPrefixes = List.of(
            "add", "addLast", "put", "append", "push", "pop", "offer", "offerLast", "remove", "removeLast", "clear", "contains", "getLast", "peek", "peekLast", "pollLast", "isEmpty", "size", "element");

    public SequenceTreeBuilder(Class<?> clazz) {
        this.clazz = clazz;
        this.methodSequence = new ArrayList<>();
        this.appliedMutators = new ArrayList<>();
        this.stepInputs = new ArrayList<>();
        this.stepOutputs = new ArrayList<>();
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
                Object[] args = generateSimpleRandomArgs(mutator);
                Object result = mutator.invoke(baseObject, args);

                methodSequence.add(mutator.getName());
                stepInputs.add(args);
                stepOutputs.add(result);
                appliedMutators.add(mutator);

            } catch (Exception e) {
                // Skip silently, try next mutator
            }
        }
    }

    private Method pickRandomMutator(Method[] allMethods) {
        Method[] mutators = Arrays.stream(allMethods)
                .filter(m -> Modifier.isPublic(m.getModifiers()) && !Modifier.isStatic(m.getModifiers()))
                .filter(m -> mutatorPrefixes.stream().anyMatch(prefix -> m.getName().equals(prefix)))
                .toArray(Method[]::new);

        Method mutator = mutators.length > 0 ? mutators[new Random().nextInt(mutators.length)] : null;        
        return mutator;
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
        Object[] targetArgs = generateSimpleRandomArgs(targetMethod);
        appliedMutators.add(targetMethod);
        methodSequence.add(targetMethod.getName());
        try {
            Object output = targetMethod.invoke(baseObject, targetArgs); 
            // Skip NaN/Infinite outputs for the target step
            if (output instanceof Double d && (Double.isNaN(d) || Double.isInfinite(d))) return null;
            if (output instanceof Float f && (Float.isNaN(f) || Float.isInfinite(f))) return null;

            // Append target step inputs/outputs
            stepInputs.add(targetArgs);
            stepOutputs.add(output);

            // Package per-step inputs and outputs
            Object[] inputsPerStep = (Object[]) (Object) stepInputs.toArray(new Object[0][]);
            Object[] outputsPerStep = stepOutputs.toArray(new Object[0]);

            return new SequenceInputOutputPair<>(methodSequence, inputsPerStep, outputsPerStep);

        } catch (Exception e) {
            // Record error at target step and still return the accumulated steps
            stepInputs.add(targetArgs);
            stepOutputs.add("error");

            Object[] inputsPerStep = (Object[]) (Object) stepInputs.toArray(new Object[0][]);
            Object[] outputsPerStep = stepOutputs.toArray(new Object[0]);
            return new SequenceInputOutputPair<>(methodSequence, inputsPerStep, outputsPerStep);
        }
    }

    public static Object[] generateSimpleRandomArgs(Method method) {
        Class<?>[] paramTypes = method.getParameterTypes();
        Object[] args = new Object[paramTypes.length];
        for (int i = 0; i < paramTypes.length; i++) {
            args[i] = randomSimpleValueForType(paramTypes[i]);
        }
        return args;
    }

    private static Object randomSimpleValueForType(Class<?> type) {
    Random rand = new Random();
    return switch (type.getSimpleName()) {
        case "int", "Integer" -> biasedInt(rand);
        case "long", "Long" -> rand.nextLong();
        case "double", "Double" -> rand.nextDouble();
        case "float", "Float" -> rand.nextFloat();
        case "boolean", "Boolean" -> rand.nextBoolean();
        case "String" -> UUID.randomUUID().toString();
        default -> {
            int choice = rand.nextInt(3); // 0, 1, or 2
            yield switch (choice) {
                case 0 -> biasedInt(rand);                // Integer
                case 1 -> rand.nextBoolean();             // Boolean
                default -> UUID.randomUUID().toString();  // String
            };
        }
    };
}

private static int biasedInt(Random rand) {
    // 70% chance small number (0–2), 30% chance bigger number
    if (rand.nextDouble() < 0.7) {
        return rand.nextInt(3); // 0, 1, or 2
    } else {
        return rand.nextInt(1000); // full range
    }
}

}
