

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_1_1 = Float.valueOf(args[1]);
        Float input_2_0 = Float.valueOf(args[2]);
        Float input_2_1 = Float.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = Float.compare(input_1_0, input_1_1);
        Integer output_2 = Float.compare(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == 1 && output_2 == -1) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

