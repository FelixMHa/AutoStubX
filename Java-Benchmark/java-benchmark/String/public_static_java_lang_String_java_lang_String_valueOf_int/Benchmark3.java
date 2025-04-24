

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        String output_1 = String.valueOf(input_1_0);
        String output_2 = String.valueOf(input_2_0);

        
        // Compare output
        if (output_1.equals("134") && output_2.equals("-2591")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

