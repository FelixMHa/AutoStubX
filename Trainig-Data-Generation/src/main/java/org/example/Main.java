package org.example;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.stream.JsonReader;

import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.List;

public class Main {

    public static int MAX_SAMPLES = 10000;
    public static final boolean EXTENDED = false;

    public static void main(String[] args) throws IOException, ClassNotFoundException {


        // generate training data for all classes in java_classes.json
        Gson gson = new Gson();
        JsonReader reader = new JsonReader(new FileReader("java_classes.json"));
        List<String> data = gson.fromJson(reader, List.class);

        String[] classesInScope = new String[]{
                //"java.lang.Boolean",
                //"java.lang.Double",
                //"java.lang.Float",
                //"java.lang.String",
                //"java.lang.Byte",
                //"java.lang.Short",
                //"java.lang.Character",
                //"java.lang.Integer",
                //"java.lang.Long",
                //"java.lang.Math",
                //"java.lang.StrictMath",
                "java.util.ArrayList",
                //"java.util.Map",
                //"java.util.HashMap",
                "java.util.LinkedList",
                //"java.util.List",
                //"java.util.Set",
                //"java.util.HashSet",
                //"java.util.TreeSet",
                //"java.util.LinkedHashSet",
                "java.util.Queue",
                "java.util.Deque",
                "java.util.Stack",
                //"java.util.Vector",
                //"java.util.Arrays",
                //"java.util.Collections"
        };

        // generate training data for each class
        for (String className : data) {

            try {
                // get class by name
                Class<?> clazz = Class.forName(className);

                // check if class is in scope
                boolean inScope = Arrays.asList(classesInScope).contains(clazz.getName());
                if (!inScope)
                    continue;

                
                GenerateTrainingDataPerClass.generateTrainingData(clazz);
            } catch (IllegalArgumentException e) {
                System.out.println("Illegal Argument Exception while generating training data for " + className);
                e.printStackTrace();
                System.exit(1);
            } catch (Exception e) {
                //System.out.println("Error while generating training data for " + className);
                //e.printStackTrace();
            }
        }

        printStatistics();

        // save mapping of class names to method names using gson
        Gson gsonPretty = new GsonBuilder().setPrettyPrinting().create();
        String json = gsonPretty.toJson(GenerateTrainingDataPerClass.successfulMethods);
        Files.write(Paths.get("methods_in_scope.json"), json.getBytes());
    }


    static void printStatistics() {
        double avg_time = (double) GenerateTrainingDataPerClass.statistics_total_time / GenerateTrainingDataPerClass.statistics_successful_methods;
        int total_params = GenerateTrainingDataPerClass.statistics_data_diversity_integer + GenerateTrainingDataPerClass.statistics_data_diversity_decimal + GenerateTrainingDataPerClass.statistics_data_diversity_boolean + GenerateTrainingDataPerClass.statistics_data_diversity_string;
        double data_diversity_integer = (double) GenerateTrainingDataPerClass.statistics_data_diversity_integer / total_params * 100;
        double data_diversity_decimal = (double) GenerateTrainingDataPerClass.statistics_data_diversity_decimal / total_params * 100;
        double data_diversity_boolean = (double) GenerateTrainingDataPerClass.statistics_data_diversity_boolean / total_params * 100;
        double data_diversity_string = (double) GenerateTrainingDataPerClass.statistics_data_diversity_string / total_params * 100;
        double data_diversity_list = (double) GenerateTrainingDataPerClass.statistics_data_diversity_list / total_params * 100;

        System.out.println("----------");
        System.out.println("Total classes & " + GenerateTrainingDataPerClass.statistics_total_classes + "\\\\");
        System.out.println("Total methods & " + GenerateTrainingDataPerClass.statistics_total_methods + "\\\\");
        System.out.println("Methods in scope & " + GenerateTrainingDataPerClass.statistics_successful_methods + "\\\\");
        System.out.println("Avg. time per method (" + GenerateTrainingDataPerClass.statistics_samples_per_method + " samples) & " + String.format("%.0f", avg_time) + "ms \\\\");
        System.out.println("Data diversity & " + String.format("%.0f", data_diversity_integer) + "\\% Integer \\\\\n" +
                "& " + String.format("%.0f", data_diversity_decimal) + "\\% Decimal \\\\\n" +
                "& " + String.format("%.0f", data_diversity_boolean) + "\\% Boolean \\\\\n" +
                "& " + String.format("%.0f", data_diversity_string) + "\\% String \\\\\n" +
                "& " + String.format("%.0f", data_diversity_list) + "\\% List \\\\");
        System.out.println("----------");
    }
}