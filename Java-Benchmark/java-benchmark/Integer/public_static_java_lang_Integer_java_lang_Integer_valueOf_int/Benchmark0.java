

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Integer.valueOf(input_1_0);
        Integer output_2 = Integer.valueOf(input_2_0);

        
        // Compare output
        if (output_1 == 2147483647 && output_2 == -654) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

