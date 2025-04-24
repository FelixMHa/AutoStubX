

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Math.round(input_1_0);
        Integer output_2 = Math.round(input_2_0);

        
        // Compare output
        if (output_1 == 0 && output_2 == -2147483648) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

