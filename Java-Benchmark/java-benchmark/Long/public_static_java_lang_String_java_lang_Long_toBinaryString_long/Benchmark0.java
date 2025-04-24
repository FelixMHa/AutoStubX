

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toBinaryString(input_1_0);
        String output_2 = Long.toBinaryString(input_2_0);

        
        // Compare output
        if (output_1.equals("1111111111111111111111111111111111111111101010000001000100011010") && output_2.equals("1111101001000101000100100100011001101000001101110101010111101111")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

