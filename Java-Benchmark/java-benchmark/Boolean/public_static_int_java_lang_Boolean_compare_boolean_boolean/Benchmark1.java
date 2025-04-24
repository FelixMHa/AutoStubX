

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Boolean input_1_0 = Boolean.valueOf(args[0]);
        Boolean input_1_1 = Boolean.valueOf(args[1]);
        Boolean input_2_0 = Boolean.valueOf(args[2]);
        Boolean input_2_1 = Boolean.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = Boolean.compare(input_1_0, input_1_1);
        Integer output_2 = Boolean.compare(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == 0 && output_2 == 1) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

