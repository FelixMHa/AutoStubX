

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toBinaryString(input_1_0);
        String output_2 = Long.toBinaryString(input_2_0);

        
        // Compare output
        if (output_1.equals("1111111111111111111111111111111111110110111111011110001011010000") && output_2.equals("1111111111111111111111111111111111101011100000110010110111110100")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

