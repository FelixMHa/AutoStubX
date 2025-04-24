

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = Float.toString(input_1_0);
        String output_2 = Float.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("1.183214E-11") && output_2.equals("-3.060394E-11")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

