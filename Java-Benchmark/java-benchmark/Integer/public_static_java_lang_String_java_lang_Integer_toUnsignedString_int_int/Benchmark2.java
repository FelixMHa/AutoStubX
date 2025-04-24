

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        Integer input_2_0 = Integer.valueOf(args[2]);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        String output_1 = Integer.toUnsignedString(input_1_0, input_1_1);
        String output_2 = Integer.toUnsignedString(input_2_0, input_2_1);

        
        // Compare output
        if (output_1.equals("245") && output_2.equals("776211785")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

