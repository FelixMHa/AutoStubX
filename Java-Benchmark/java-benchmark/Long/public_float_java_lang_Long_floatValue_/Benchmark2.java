

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Float output_1 = input_1_0.floatValue();
        Float output_2 = input_2_0.floatValue();

        
        // Compare output
        if (output_1 == 8137972100000.0 && output_2 == 29195996500000.0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

