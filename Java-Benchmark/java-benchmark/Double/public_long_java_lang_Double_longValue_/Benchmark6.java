

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Long output_1 = input_1_0.longValue();
        Long output_2 = input_2_0.longValue();

        
        // Compare output
        if (output_1 == -9223372036854775808L && output_2 == 0L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

