

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        String output_1 = Integer.toBinaryString(input_1_0);
        String output_2 = Integer.toBinaryString(input_2_0);

        
        // Compare output
        if (output_1.equals("101010100100") && output_2.equals("11111111111111111111111111111010")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

