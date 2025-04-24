

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        String output_1 = Integer.toBinaryString(input_1_0);
        String output_2 = Integer.toBinaryString(input_2_0);

        
        // Compare output
        if (output_1.equals("0") && output_2.equals("1110110111111011100000111101")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

