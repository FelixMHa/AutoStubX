

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toHexString(input_1_0);
        String output_2 = Double.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("0x1.ef944291f06c8p-368") && output_2.equals("-0x1.f633d13591bdcp197")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

