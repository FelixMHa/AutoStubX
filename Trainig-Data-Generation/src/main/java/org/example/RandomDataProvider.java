package org.example;

import java.lang.reflect.Method;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.NavigableSet;
import java.util.Queue;
import java.util.Random;
import java.util.Set;
import java.util.SortedSet;
import java.util.TreeSet;

public class RandomDataProvider {

    private static Random random = new Random();

    public static Object randomValueForType(Class<?> type) {
        // This method should be extended to handle more types as needed.
        if (type.equals(int.class) || type.equals(Integer.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;

            // get special values
            if (random.nextDouble() < 0.05) {
                int[] specialValues = { Integer.MIN_VALUE, Integer.MAX_VALUE, 0, 1, -1 };
                return specialValues[random.nextInt(specialValues.length)];
            }

            // get random number from 0 to bits
            int bitsCnt = random.nextInt(Integer.SIZE - 1) + 1;

            // return random number in range
            int randomInt = random.nextInt((int) (1 << bitsCnt) - 1);

            // get random sign
            if (random.nextBoolean()) {
                randomInt = -randomInt;
            }
            return randomInt;
        } else if (type.equals(double.class) || type.equals(Double.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_decimal++;

            // get special values
            if (random.nextDouble() < 0.05) {
                double[] specialValues = { Double.MIN_VALUE, Double.MAX_VALUE, 0, 1, -1, Double.NaN,
                        Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY };
                return specialValues[random.nextInt(specialValues.length)];
            }

            // get a double with random exponent
            double randomDouble = Math.pow(2, random.nextInt(1024) - 512) * random.nextDouble();

            // get random sign
            if (random.nextBoolean()) {
                randomDouble = -randomDouble;
            }
            return randomDouble;
        } else if (type.equals(float.class) || type.equals(Float.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_decimal++;

            // get special values
            if (random.nextDouble() < 0.05) {
                float[] specialValues = { Float.MIN_VALUE, Float.MAX_VALUE, 0, 1, -1, Float.NaN,
                        Float.POSITIVE_INFINITY, Float.NEGATIVE_INFINITY };
                return specialValues[random.nextInt(specialValues.length)];
            }

            // Generate a float with random exponent
            float randomFloat = (float) (Math.pow(2, random.nextInt(256) - 127) * random.nextFloat());

            if (random.nextBoolean()) {
                randomFloat = -randomFloat;
            }
            return randomFloat;
        } else if (type.equals(long.class) || type.equals(Long.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;

            // get special values
            if (random.nextDouble() < 0.05) {
                long[] specialValues = { Long.MIN_VALUE, Long.MAX_VALUE, 0, 1, -1 };
                return specialValues[random.nextInt(specialValues.length)];
            }

            // get number of bits
            int bitsCnt = random.nextInt(63) + 1;
            long randomLong = random.nextLong() & ((1L << bitsCnt) - 1);
            if (random.nextBoolean()) {
                randomLong = -randomLong;
            }
            return randomLong;
        } else if (type.equals(short.class) || type.equals(Short.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;

            // get special values
            if (random.nextDouble() < 0.05) {
                short[] specialValues = { Short.MIN_VALUE, Short.MAX_VALUE, 0, 1, -1 };
                return specialValues[random.nextInt(specialValues.length)];
            }

            // Generate a random number of bits between 1 and 15
            int bitsCnt = random.nextInt(15) + 1;

            // Generate a random short with up to bitsCnt bits
            short randomShort = (short) (random.nextInt(1 << bitsCnt) & ((1 << bitsCnt) - 1));

            // Randomly negate the number
            if (random.nextBoolean()) {
                randomShort = (short) -randomShort;
            }
            return randomShort;
        } else if (type.equals(byte.class) || type.equals(Byte.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;

            // get special values
            if (random.nextDouble() < 0.05) {
                byte[] specialValues = { Byte.MIN_VALUE, Byte.MAX_VALUE, 0, 1, -1 };
                return specialValues[random.nextInt(specialValues.length)];
            }

            // Generate a random number of bits between 1 and 7
            int bitsCnt = random.nextInt(7) + 1;

            // Generate a random byte with up to bitsCnt bits
            byte randomByte = (byte) (random.nextInt(1 << bitsCnt) & ((1 << bitsCnt) - 1));

            // Randomly negate the number
            if (random.nextBoolean()) {
                randomByte = (byte) -randomByte;
            }
            return randomByte;
        } else if (type.equals(boolean.class) || type.equals(Boolean.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_boolean++;
            return random.nextBoolean();
        } else if (type.equals(char.class) || type.equals(Character.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;
            // Generate a random number of bits between 1 and 16
            int bitsCnt = random.nextInt(15) + 1;
            return (char) (random.nextInt(1 << bitsCnt));
        } else if (type.equals(String.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_string++;
            // generate random string
            int length = random.nextInt(10);
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < length; i++) {
                sb.append((char) random.nextInt(256));
            }
            return sb.toString();
        }
        // Primitive arrays like int[], double[], etc.
        else if (type.isArray()) {
            Class<?> component = type.getComponentType();
            int len = 2 + random.nextInt(3);

            if (component.isPrimitive()) {
                if (component == int.class) {
                    int[] arr = new int[len];
                    for (int i = 0; i < len; i++)
                        arr[i] = random.nextInt(100);
                    return arr;
                } else if (component == double.class) {
                    double[] arr = new double[len];
                    for (int i = 0; i < len; i++)
                        arr[i] = random.nextDouble() * 100;
                    return arr;
                } else if (component == boolean.class) {
                    boolean[] arr = new boolean[len];
                    for (int i = 0; i < len; i++)
                        arr[i] = random.nextBoolean();
                    return arr;
                } else if (component == long.class) {
                    long[] arr = new long[len];
                    for (int i = 0; i < len; i++)
                        arr[i] = random.nextLong();
                    return arr;
                } else if (component == float.class) {
                    float[] arr = new float[len];
                    for (int i = 0; i < len; i++)
                        arr[i] = random.nextFloat();
                    return arr;
                } else if (component == char.class) {
                    char[] arr = new char[len];
                    for (int i = 0; i < len; i++)
                        arr[i] = (char) (random.nextInt(26) + 'a');
                    return arr;
                } else if (component == short.class) {
                    short[] arr = new short[len];
                    for (int i = 0; i < len; i++)
                        arr[i] = (short) random.nextInt(Short.MAX_VALUE);
                    return arr;
                } else if (component == byte.class) {
                    byte[] arr = new byte[len];
                    random.nextBytes(arr);
                    return arr;
                }
            } else {
                // Object arrays (e.g. String[], Object[])
                Object[] array = (Object[]) java.lang.reflect.Array.newInstance(component, len);
                for (int i = 0; i < len; i++) {
                    array[i] = randomPrimitiveOrString(); // You could use recursive generation here too
                }
                return array;
            }
        }

        // Collections & Lists, Sets, Queues, Deques, etc.
        else if (Collection.class.isAssignableFrom(type)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_list++;

            List<Object> values = new ArrayList<>();
            int length = 2 + random.nextInt(4); // 2–5 items
            for (int i = 0; i < length; i++) {
                values.add(randomValueForType(Object.class));
            }

            if (List.class.isAssignableFrom(type)) {
                return new ArrayList<>(values);
            } else if (Set.class.isAssignableFrom(type)) {
                return new HashSet<>(values);
            } else if (Queue.class.isAssignableFrom(type)) {
                return new LinkedList<>(values);
            } else if (Deque.class.isAssignableFrom(type)) {
                return new ArrayDeque<>(values);
            } else if (SortedSet.class.isAssignableFrom(type)) {
                return new TreeSet<>(values);
            } else if (NavigableSet.class.isAssignableFrom(type)) {
                return new TreeSet<>(values);
            } else {
                return values; // fallback raw collection
            }
        }

        // Maps
        else if (Map.class.isAssignableFrom(type)) {
            Map<Object, Object> map = new HashMap<>();
            for (int i = 0; i < 3; i++) {
                map.put(randomPrimitiveOrString(), randomPrimitiveOrString());
            }
            return map;
        }

        // Functional Interfaces
        else if (java.util.function.Predicate.class.isAssignableFrom(type)) {
            return (java.util.function.Predicate<Object>) o -> true;
        } else if (java.util.function.Function.class.isAssignableFrom(type)) {
            return (java.util.function.Function<Object, Object>) o -> randomPrimitiveOrString();
        } else if (java.util.function.Consumer.class.isAssignableFrom(type)) {
            return (java.util.function.Consumer<Object>) o -> {
                /* no-op */ };
        } else if (java.util.function.Supplier.class.isAssignableFrom(type)) {
            return (java.util.function.Supplier<Object>) RandomDataProvider::randomPrimitiveOrString;
        } else if (java.util.function.BiFunction.class.isAssignableFrom(type)) {
            return (java.util.function.BiFunction<Object, Object, Object>) (k, v) -> v;
        }
        // Generic Object (fallback for generic types)
        else if (type.equals(Object.class)) {
            return randomPrimitiveOrString();
        } else if (java.util.Comparator.class.isAssignableFrom(type)) {
            // Return a comparator that randomly returns -1, 0, or 1
            return (java.util.Comparator<Object>) (o1, o2) -> {
                int[] results = { -1, 0, 1 };
                return results[random.nextInt(3)];
            };
        } else if (type.equals(Class.class)) {
            // Return a random class, sometimes an array class
            Class<?>[] baseClasses = { String.class, Integer.class, Double.class, Boolean.class, Object.class };
            if (random.nextBoolean()) {
                // Return a base class
                return baseClasses[random.nextInt(baseClasses.length)];
            } else {
                // Return an array class
                Class<?> base = baseClasses[random.nextInt(baseClasses.length)];
                return java.lang.reflect.Array.newInstance(base, 0).getClass();
            }
        }

        throw new IllegalArgumentException("Type " + type + " not supported");
    }

    public static Object[] generateRandomArgs(Method method) {
        Class<?>[] paramTypes = method.getParameterTypes();
        Object[] args = new Object[paramTypes.length];
        for (int i = 0; i < paramTypes.length; i++) {
            args[i] = randomValueForType(paramTypes[i]);
        }
        return args;
    }

    private static Object randomPrimitiveOrString() {
        int pick = random.nextInt(4);
        switch (pick) {
            case 0:
                return randomValueForType(Integer.class);
            case 1:
                return randomValueForType(Double.class);
            case 2:
                return randomValueForType(Boolean.class);
            default:
                return randomValueForType(String.class);
        }
    }
}
