

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = Float.toString(input_1_0);
        String output_2 = Float.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("3.0993967E-9") && output_2.equals("1.4E-45")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

