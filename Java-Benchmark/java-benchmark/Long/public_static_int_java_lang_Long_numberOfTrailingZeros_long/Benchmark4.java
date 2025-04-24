

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Long.numberOfTrailingZeros(input_1_0);
        Integer output_2 = Long.numberOfTrailingZeros(input_2_0);

        
        // Compare output
        if (output_1 == 1 && output_2 == 2) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

