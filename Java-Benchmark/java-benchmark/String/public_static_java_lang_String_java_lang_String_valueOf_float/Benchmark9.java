

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = String.valueOf(input_1_0);
        String output_2 = String.valueOf(input_2_0);

        
        // Compare output
        if (output_1.equals("-4.1831456E36") && output_2.equals("-5.33577E-27")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

