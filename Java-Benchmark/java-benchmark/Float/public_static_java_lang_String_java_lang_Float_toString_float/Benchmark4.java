

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = Float.toString(input_1_0);
        String output_2 = Float.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("1.95858432E8") && output_2.equals("2.8376996E-7")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

