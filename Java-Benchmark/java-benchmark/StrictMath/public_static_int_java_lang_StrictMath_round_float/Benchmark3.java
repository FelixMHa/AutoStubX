

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = StrictMath.round(input_1_0);
        Integer output_2 = StrictMath.round(input_2_0);

        
        // Compare output
        if (output_1 == -1 && output_2 == 0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

