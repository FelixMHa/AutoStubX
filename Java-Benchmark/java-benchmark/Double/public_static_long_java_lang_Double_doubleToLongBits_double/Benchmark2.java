

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Double.doubleToLongBits(input_1_0);
        Long output_2 = Double.doubleToLongBits(input_2_0);

        
        // Compare output
        if (output_1 == -2628253675492989300L && output_2 == 2532665460927912048L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

