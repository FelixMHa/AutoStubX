

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toBinaryString(input_1_0);
        String output_2 = Long.toBinaryString(input_2_0);

        
        // Compare output
        if (output_1.equals("11110101101010111100101010100001101101000111110111") && output_2.equals("1111111111111111111111111111111111111111111111101010011001100100")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

