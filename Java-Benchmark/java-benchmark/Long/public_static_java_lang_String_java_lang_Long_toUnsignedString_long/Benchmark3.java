

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toUnsignedString(input_1_0);
        String output_2 = Long.toUnsignedString(input_2_0);

        
        // Compare output
        if (output_1.equals("450") && output_2.equals("131256861645183731")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

