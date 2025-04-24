

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = StrictMath.getExponent(input_1_0);
        Integer output_2 = StrictMath.getExponent(input_2_0);

        
        // Compare output
        if (output_1 == 100 && output_2 == 103) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

