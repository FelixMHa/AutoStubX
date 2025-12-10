package org.example;

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.*;



public class SequenceTreeBuilder {


    private final Object baseObject;
    private final List<String> sequence;
    private final List<Object> stepInputs;
    private final List<Object> stepOutputs;
    private final Random random = new Random();
    private final List<Method> validMethods;

    public SequenceTreeBuilder(Class<?> clazz) {
        this.sequence = new ArrayList<>();
        this.stepInputs = new ArrayList<>();
        this.stepOutputs = new ArrayList<>();
        this.baseObject = createInstance(clazz);
        this.validMethods = getValidMethods(clazz);
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

        // ✅ 70% chance: pre-fill instance with 0–3 random elements
        if (instance instanceof Collection<?> && random.nextDouble() < 0.7) {
            int count = random.nextInt(4);
            Collection<Object>  coll = (Collection<Object>) instance;
            for (int i = 0; i < count; i++) {
                Object randomElement = RandomDataProvider.randomPrimitiveOrString();
                boolean out = coll.add(randomElement);
                sequence.add("add#obj");
                stepInputs.add(new Object[]{randomElement});
                stepOutputs.add(out);
            }
        return coll;
        } else if (instance instanceof Map<?, ?> && random.nextDouble() < 0.7) {
            int count = random.nextInt(4);
            Map<Object, Object> map = (Map<Object, Object>) instance;
            for (int i = 0; i < count; i++) {
                Object randomKey = RandomDataProvider.randomPrimitiveOrString();
                Object randomValue = RandomDataProvider.randomPrimitiveOrString();
                Object out = map.put(randomKey, randomValue);
                sequence.add("put#obj_obj");
                stepInputs.add(new Object[]{randomKey, randomValue});
                stepOutputs.add(out);
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


        while (sequence.size() < steps) {
            Method candidate = validMethods.get(random.nextInt(validMethods.size()));
            if (candidate == null) continue;
            Object[] args = RandomDataProvider.generateRandomArgs(candidate, baseObject);
            String methodSig = createMethodSignature(candidate);
            sequence.add(methodSig); 
            stepInputs.add(args);
            try {
                Object output = candidate.invoke(baseObject, args);
                stepOutputs.add(output);

            } catch (Exception e) {
                stepOutputs.add("error");
                
            }
        }
        return new SequenceInputOutputPair<>(
                sequence,
                stepInputs.toArray(),
                stepOutputs.toArray()
        );
    }
    private String normalizeType(Class<?> type) {
        // Primitive types
        if (type == int.class) return "int";
        if (type == boolean.class) return "bool";
        if (type == float.class) return "float";
        if (type == double.class) return "float";  // Treat double as float
        if (type == long.class) return "long";
        if (type == byte.class) return "int";      // Small ints
        if (type == short.class) return "int";     // Small ints
        if (type == char.class) return "char";
        
        // Everything else is an object
        // This includes: Object, String, E (generic), T, K, V, Integer (boxed), etc.
        return "obj";
    }
    private String createMethodSignature(Method method) {
        String methodName = method.getName();
        Class<?>[] paramTypes = method.getParameterTypes();
        
        if (paramTypes.length == 0) {
            return methodName + "#0";
        }
        
        StringBuilder sig = new StringBuilder(methodName).append("#");
        for (int i = 0; i < paramTypes.length; i++) {
            if (i > 0) sig.append("_");
            sig.append(normalizeType(paramTypes[i]));
        }
        
        return sig.toString();
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
        return  candidates;
    }



    
}