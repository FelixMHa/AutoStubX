

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Long.highestOneBit(input_1_0);
        Long output_2 = Long.highestOneBit(input_2_0);

        
        // Compare output
        if (output_1 == 8388608L && output_2 == 549755813888L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

