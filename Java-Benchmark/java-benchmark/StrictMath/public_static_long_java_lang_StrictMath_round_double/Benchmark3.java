

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Long output_1 = StrictMath.round(input_1_0);
        Long output_2 = StrictMath.round(input_2_0);

        
        // Compare output
        if (output_1 == 0L && output_2 == 9223372036854775807L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

