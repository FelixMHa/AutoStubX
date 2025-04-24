

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = String.valueOf(input_1_0);
        String output_2 = String.valueOf(input_2_0);

        
        // Compare output
        if (output_1.equals("-0.010825649") && output_2.equals("-1.5870069E32")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

