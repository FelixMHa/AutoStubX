

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Float.floatToIntBits(input_1_0);
        Integer output_2 = Float.floatToIntBits(input_2_0);

        
        // Compare output
        if (output_1 == 239525621 && output_2 == 120930812) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

