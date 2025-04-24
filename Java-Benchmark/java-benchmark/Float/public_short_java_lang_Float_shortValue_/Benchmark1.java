

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Short output_1 = input_1_0.shortValue();
        Short output_2 = input_2_0.shortValue();

        
        // Compare output
        if (output_1 == 0 && output_2 == 2299) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

