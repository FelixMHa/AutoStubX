

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toBinaryString(input_1_0);
        String output_2 = Long.toBinaryString(input_2_0);

        
        // Compare output
        if (output_1.equals("1111100010100010001001010011011110010100011111100111010001011100") && output_2.equals("11101000010100010000000100100010011101011100")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

