

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Long output_1 = input_1_0.longValue();
        Long output_2 = input_2_0.longValue();

        
        // Compare output
        if (output_1 == 9223372036854775807L && output_2 == 0L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

