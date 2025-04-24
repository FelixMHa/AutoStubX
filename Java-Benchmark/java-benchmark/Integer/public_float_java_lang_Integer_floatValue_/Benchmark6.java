

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Float output_1 = input_1_0.floatValue();
        Float output_2 = input_2_0.floatValue();

        
        // Compare output
        if (output_1 == 2.0 && output_2 == -2610.0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

