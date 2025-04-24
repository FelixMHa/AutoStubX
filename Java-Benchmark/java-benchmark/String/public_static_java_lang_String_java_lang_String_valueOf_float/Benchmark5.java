

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = String.valueOf(input_1_0);
        String output_2 = String.valueOf(input_2_0);

        
        // Compare output
        if (output_1.equals("9.660623E34") && output_2.equals("5.485369E-7")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

