

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Long.reverse(input_1_0);
        Long output_2 = Long.reverse(input_2_0);

        
        // Compare output
        if (output_1 == 6394386977412644864L && output_2 == 4301735925813390335L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

