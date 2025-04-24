

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("-2.0421595E21") && output_2.equals("-8.852461E-18")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

