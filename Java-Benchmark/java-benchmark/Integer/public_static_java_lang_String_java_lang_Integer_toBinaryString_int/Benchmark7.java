

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        String output_1 = Integer.toBinaryString(input_1_0);
        String output_2 = Integer.toBinaryString(input_2_0);

        
        // Compare output
        if (output_1.equals("11111111111111110110110101111100") && output_2.equals("11100100011011010111001010")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

