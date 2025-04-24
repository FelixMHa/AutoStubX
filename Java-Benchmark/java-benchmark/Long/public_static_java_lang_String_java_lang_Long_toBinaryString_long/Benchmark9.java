

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toBinaryString(input_1_0);
        String output_2 = Long.toBinaryString(input_2_0);

        
        // Compare output
        if (output_1.equals("1111111111111011000001011010010001011010100010000000010100101100") && output_2.equals("1011000000011000110011110001101101")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

