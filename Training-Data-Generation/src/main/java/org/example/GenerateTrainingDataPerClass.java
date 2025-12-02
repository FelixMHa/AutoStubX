package org.example;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.io.IOException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;

import java.util.List;

public class GenerateTrainingDataPerClass {

    public static int statistics_total_classes = 0;
    public static int statistics_total_methods = 0;
    public static int statistics_successful_methods = 0;
    public static long statistics_total_time = 0;
    public static long statistics_samples_per_method = 0;
    public static int statistics_data_diversity_integer = 0;
    public static int statistics_data_diversity_string = 0;
    public static int statistics_data_diversity_decimal = 0;
    public static int statistics_data_diversity_boolean = 0;
    public static int statistics_data_diversity_list = 0;

    public static HashMap<String, JavaFunctionExport> successfulMethods = new HashMap<>();

    private static List<String> getParamTypeNames(Class<?>[] paramTypes) {
        List<String> types = new ArrayList<>();
        for (Class<?> param : paramTypes) {
            types.add(param.getTypeName());
        }
        return types;
    }

    public static void generateTrainingData(Class<?> targetClass) throws IOException {

        statistics_total_classes++;
        boolean isStateful = isStateful(targetClass.getName());

        if (isStateful) {
            generateStatefulTrainingDataForClass(targetClass);
        } else {
            generateStatelessTrainingDataForClass(targetClass);
        }

    }

    private static void generateStatefulTrainingDataForClass(Class<?> targetClass) throws  IOException {
        List<SequenceInputOutputPair<Object[], Object>> trainingData = new ArrayList<>();
        long startTime = System.currentTimeMillis();
        for (int i = 0; i < Main.MAX_SAMPLES/10; i++) {
            
            SequenceTreeBuilder builder = new SequenceTreeBuilder(targetClass);
            SequenceInputOutputPair<Object[], Object> sample = builder.buildSequence(8);
            if (sample != null) {
                trainingData.add(sample);
            }
        }
        String fileName = targetClass.toGenericString().replaceAll("[^A-Za-z0-9]", "_") + ".json";
        Path trainingDataFile = Paths.get("./symbolic-regression-data/training/" + fileName);
        writeTrainingDataToFile(trainingDataFile, trainingData, startTime);
    }

    private static void generateStatelessTrainingDataForClass(Class<?> targetClass) throws IOException {
        Method[] methods = targetClass.getDeclaredMethods();
        for (Method method : methods) {
            statistics_total_methods++;

            if (!Modifier.isPublic(method.getModifiers()))
                continue;

            // block list
            if (targetClass.getName().equals("java.lang.System"))
                continue;

            // Debug
            // if (!method.getName().contains("isDefined"))
            // continue;

            // make sure the return value is not void
            Class<?> returnType = method.getReturnType();
            String returnTypeName = returnType.getName();

            List<String> disallowedReturnTypePrefixes = List.of(
                    "java.util.Iterator",
                    "java.util.ListIterator",
                    "java.util.Enumeration",
                    "java.util.Spliterator",
                    "java.util.stream.Stream");

            boolean isDisallowedReturnType = returnType.equals(Void.TYPE)
                    || returnType.equals(Void.class)
                    || disallowedReturnTypePrefixes.stream().anyMatch(returnTypeName::startsWith)
                    || !(isPrimitive(returnType) || returnType.equals(String.class));

            if (isDisallowedReturnType) {
                continue;
            }

            // extract parameter types
            Class<?>[] paramTypes = method.getParameterTypes();

            // check if all parameter types are primitives or strings
            boolean isStatic = Modifier.isStatic(method.getModifiers());
            if (isStatic &&
                    Arrays.stream(paramTypes)
                            .filter(p -> !isPrimitive(p) && !p.equals(String.class))
                            .count() == 0 // only primitives or strings
                    && paramTypes.length > 0 // at least one parameter
                    || !isStatic && (Arrays.stream(paramTypes)
                            .filter(p -> !isPrimitive(p) && !p.equals(String.class))
                            .count() == 0 // If not static, then all parameters are primitives or strings
                            || paramTypes.length == 0 // or no parameters
                    )) {
                System.out.println("Method: " + method.getName());
                System.out.println("Parameter types: " + Arrays.toString(paramTypes));
                System.out.println("Return type: " + method.getReturnType());
                try {
                    generateTrainingDataForMethod(method, isStatic, targetClass.getName());
                } catch (OutOfMemoryError x) {
                    System.out.println("Out of memory error while generating training data for " + method.getName());
                }
                System.out.println("---");
            }
        }
    }

    private static boolean isPrimitive(Class<?> c) {
        if (c.isPrimitive())
            return true;

        String className = c.getName();
        if (className.equals("java.lang.Integer"))
            return true;
        if (className.equals("java.lang.Double"))
            return true;
        if (className.equals("java.lang.Float"))
            return true;
        if (className.equals("java.lang.Boolean"))
            return true;
        if (className.equals("java.lang.Short"))
            return true;
        if (className.equals("java.lang.Long"))
            return true;
        if (className.equals("java.lang.Character"))
            return true;
        if (className.equals("java.lang.Byte"))
            return true;

        return false;
    }

    private static boolean isStateful(String className) {
        return className.equals("java.util.Stack") ||
                className.equals("java.util.ArrayList") ||
                className.equals("java.util.Map") ||
                className.equals("java.util.HashMap") ||
                className.equals("java.util.LinkedList") ||
                className.equals("java.util.List") ||
                className.equals("java.util.Set") ||
                className.equals("java.util.HashSet") ||
                className.equals("java.util.TreeSet") ||
                className.equals("java.util.LinkedHashSet") ||
                className.equals("java.util.Queue") ||
                className.equals("java.util.Deque") ||
                className.equals("java.util.Stack") ||
                className.equals("java.util.Vector") ||
                className.equals("java.util.Collections") ||
                className.equals("java.lang.StringBuilder");
    }

    private static void generateTrainingDataForMethod(Method method, boolean isStatic, String className)
            throws IOException {

        List<SequenceInputOutputPair<Object[], Object>> trainingData = new ArrayList<>();
        String extended = Main.EXTENDED ? ".extended." : "";
        String fileName = method.toGenericString().replaceAll("[^A-Za-z0-9]", "_") + extended + ".json";
        Path trainingDataFile = Paths.get("./symbolic-regression-data/training/" + className + "/" + fileName);

        // create folders if they don't exist
        if (!Files.exists(trainingDataFile.getParent())) {
            Files.createDirectories(trainingDataFile.getParent());
        }

        // problematic functions
        if (fileName.contains("public_java_lang_String_java_lang_String_repeat_int"))
            return;
        if (fileName.contains("public_java_lang_String_java_lang_String_indent_int"))
            return;
       

        boolean printedError = false;
        int multiplier = Main.EXTENDED ? 100 : 1;
        long startTime = System.currentTimeMillis();
        statistics_samples_per_method = Main.MAX_SAMPLES * multiplier;
        for (int i = 0; i < Main.MAX_SAMPLES * multiplier; i++) {
            Object[] args = RandomDataProvider.generateRandomArgs(method, null);
            List<String> sequence = Collections.emptyList();
            try {
                Object baseObject = null;
                String stringRepresentation = null;

                if (!isStatic) {
                    baseObject = RandomDataProvider.randomValueForType(method.getDeclaringClass());
                }
                stringRepresentation = String.valueOf(baseObject);
                Object output = method.invoke(baseObject, args);

                // skip invalid outputs
                if (!isStatic && !stringRepresentation.equals(String.valueOf(baseObject)))
                    continue;
                if (output instanceof Double && (Double.isNaN((Double) output) || Double.isInfinite((Double) output)))
                    continue;
                if (output instanceof Float && (Float.isNaN((Float) output) || Float.isInfinite((Float) output)))
                    continue;

                // Always wrap into a per-step sequence of length 1
                sequence = Collections.singletonList(method.getName());
                Object[][] inputsPerStep = new Object[][] { args };
                Object[] outputsPerStep = new Object[] { output };
                trainingData.add(new SequenceInputOutputPair<>(sequence, inputsPerStep, outputsPerStep));
            } catch (Exception e) {
                if (!printedError) {
                    printedError = true;
                    System.out.println("Error while invoking method " + method.getName() + ": " + e.getMessage());
                }
                sequence = Collections.singletonList(method.getName());
                Object[][] inputsPerStep = new Object[][] { args };
                Object[] outputsPerStep = new Object[] { "error" };
                trainingData.add(new SequenceInputOutputPair<>(sequence, inputsPerStep, outputsPerStep));
            }
        }
        if (trainingData.size() == Main.MAX_SAMPLES * multiplier) {
                statistics_successful_methods++;
        writeTrainingDataToFile(trainingDataFile, trainingData, startTime);
        String owner = method.getDeclaringClass().getName();
                String name = method.getName();
                String genericString = method.toGenericString();
                String returnType = method.getReturnType().getTypeName();
                List<String> paramTypes = getParamTypeNames(method.getParameterTypes());

                JavaFunctionExport javaFunctionExport = new JavaFunctionExport(
                        owner,
                        name,
                        genericString,
                        returnType,
                        paramTypes);

                successfulMethods.put(trainingDataFile.getFileName().toString(), javaFunctionExport);
        }else {
                System.out.println("Not enough samples for " + method.getName() + ", skipping.");
            }
    }

    private static void writeTrainingDataToFile(Path file, List<SequenceInputOutputPair<Object[], Object>> trainingData, long startTime)
            throws IOException {
        // create folders if they don't exist
        if (!Files.exists(file.getParent())) {
            Files.createDirectories(file.getParent());
        }
        if (trainingData.isEmpty())
            return;

        // write training data to file, replace all non-alphanumeric characters in
        // method name
        System.out.println("Writing training data to " + file.getFileName().toString());

        try {
            Gson gson = new GsonBuilder()
                    .serializeSpecialFloatingPointValues()
                    .setPrettyPrinting()
                    .create();
            String json = gson.toJson(trainingData);


                long timeDelta = System.currentTimeMillis() - startTime;
                statistics_total_time += timeDelta;

                // Only save if it was successful
                Files.writeString(file, json);
            
        } catch (Exception e) {
            System.out.println("Error while writing training data to file " + file);
            e.printStackTrace();
        }
    }

}
