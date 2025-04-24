

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Math.getExponent(input_1_0);
        Integer output_2 = Math.getExponent(input_2_0);

        
        // Compare output
        if (output_1 == -106 && output_2 == -245) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

