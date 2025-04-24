

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toOctalString(input_1_0);
        String output_2 = Long.toOctalString(input_2_0);

        
        // Compare output
        if (output_1.equals("1777777777777777776442") && output_2.equals("6300053107532342")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

