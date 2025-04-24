package org.example;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import lombok.SneakyThrows;

import java.io.IOException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
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

    public static HashMap<String, JavaFunctionExport> successfulMethods = new HashMap<>();


    public static void generateTrainingData(Class<?> targetClass) throws IOException {

        statistics_total_classes++;

        Method[] methods = targetClass.getDeclaredMethods();
        for (Method method : methods) {
            statistics_total_methods++;

            if (!Modifier.isPublic(method.getModifiers()))
                continue;

            // block list
            if (targetClass.getName().equals("java.lang.System"))
                continue;

            // Debug
            //if (!method.getName().contains("isDefined"))
            //    continue;

            // make sure the return value is not void
            if (method.getReturnType().equals(Void.class) // not void
                    || method.getReturnType().equals(Void.TYPE) // not void
                    || !(isPrimitive(method.getReturnType()) || method.getReturnType().equals(String.class))) {
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
                 || !isStatic && (
                         Arrays.stream(paramTypes)
                        .filter(p -> !isPrimitive(p) && !p.equals(String.class))
                        .count() == 0 // If not static, then all parameters are primitives or strings
                    || paramTypes.length == 0 // or no parameters
            )
            ) {
                System.out.println("Method: " + method.getName());
                System.out.println("Parameter types: " + Arrays.toString(paramTypes));
                System.out.println("Return type: " + method.getReturnType());
                try {
                    generateTrainingDataForMethod(method, isStatic);
                } catch (OutOfMemoryError x) {
                    System.out.println("Out of memory error while generating training data for " + method.getName());
                }
                System.out.println("---");
            }
        }
    }

    private static boolean isPrimitive(Class c) {
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


    private static void generateTrainingDataForMethod(Method method, boolean isStatic) throws IOException {

        List<InputOutputPair<Object[], Object>> trainingData = new ArrayList<>();
        String extended = Main.EXTENDED ? ".extended." : "";
        String fileName = method.toGenericString().replaceAll("[^A-Za-z0-9]", "_") + extended + ".json";
        Path trainingDataFile = Paths.get("./symbolic-regression-data/training/" + fileName);

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
            // generate random values
            Object[] args = new Object[method.getParameterCount()];
            for (int j = 0; j < method.getParameterCount(); j++) {
                args[j] = RandomDataProvider.randomValueForType(method.getParameterTypes()[j]);
            }

            // invoke method
            try {
                Object baseObject = null;
                String stringRepresentation = null;
                if (!isStatic) {
                    baseObject = RandomDataProvider.randomValueForType(method.getDeclaringClass());
                    stringRepresentation = String.valueOf(baseObject);
                }

                Object output = method.invoke(baseObject, args);

                // make sure the base object is still the same
                if (!isStatic && !stringRepresentation.equals(String.valueOf(baseObject)))
                    continue;

                // check if output is nan or infinity
                if (output instanceof Double && (Double.isNaN((Double) output) || Double.isInfinite((Double) output)))
                    continue;
                if (output instanceof Float && (Float.isNaN((Float) output) || Float.isInfinite((Float) output)))
                    continue;

                if (!isStatic) {
                    // add base object as first argument
                    ArrayList<Object> list = new ArrayList<>();
                    list.add(baseObject);
                    list.addAll(Arrays.asList(args));

                    args = list.toArray();
                }

                trainingData.add(new InputOutputPair<>(args, output));
            } catch (Exception e) {
                if (!printedError) {
                    printedError = true;
                    System.out.println("Error while invoking method " + method.getName() + ": " + e.getMessage());
                }
            }
        }

        if (trainingData.isEmpty())
            return;

        // write training data to file, replace all non-alphanumeric characters in method name
        System.out.println("Writing training data to " + fileName);

        try {
            Gson gson = new GsonBuilder()
                    .serializeSpecialFloatingPointValues()
                    .setPrettyPrinting()
                    .create();
            String json = gson.toJson(trainingData);

            // Check if it was successful
            if (trainingData.size() == Main.MAX_SAMPLES * multiplier) {
                statistics_successful_methods++;
                long timeDelta = System.currentTimeMillis() - startTime;
                statistics_total_time += timeDelta;

                // Only save if it was successful
                Files.writeString(trainingDataFile, json);

                String owner = method.getDeclaringClass().getName();
                String name = method.getName();
                String genericString = method.toGenericString();
                JavaFunctionExport javaFunctionExport = new JavaFunctionExport(owner, name, genericString);
                successfulMethods.put(trainingDataFile.getFileName().toString(), javaFunctionExport);
            }
        } catch (Exception e) {
            System.out.println("Error while writing training data to file " + trainingDataFile);
            e.printStackTrace();
        }
    }

}
