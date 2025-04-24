

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Long.valueOf(input_1_0);
        Long output_2 = Long.valueOf(input_2_0);

        
        // Compare output
        if (output_1 == -2088067992407906891L && output_2 == 2307983L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

