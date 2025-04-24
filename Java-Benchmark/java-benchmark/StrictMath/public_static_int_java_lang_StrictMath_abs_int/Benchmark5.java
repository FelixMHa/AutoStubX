

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = StrictMath.abs(input_1_0);
        Integer output_2 = StrictMath.abs(input_2_0);

        
        // Compare output
        if (output_1 == 18 && output_2 == 3530620) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

