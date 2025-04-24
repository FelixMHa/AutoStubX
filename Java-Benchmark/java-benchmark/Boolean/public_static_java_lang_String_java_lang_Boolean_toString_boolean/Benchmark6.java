

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Boolean input_1_0 = Boolean.valueOf(args[0]);
        Boolean input_2_0 = Boolean.valueOf(args[1]);


        // Perform computation         
        String output_1 = Boolean.toString(input_1_0);
        String output_2 = Boolean.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("true") && output_2.equals("false")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

