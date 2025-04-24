

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = StrictMath.getExponent(input_1_0);
        Integer output_2 = StrictMath.getExponent(input_2_0);

        
        // Compare output
        if (output_1 == 88 && output_2 == 382) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

