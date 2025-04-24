

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toHexString(input_1_0);
        String output_2 = Double.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("0x1.0ee585c453bfp-76") && output_2.equals("-0x1.743b1ea8d421cp-341")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

