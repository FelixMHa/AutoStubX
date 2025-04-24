

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Long output_1 = input_1_0.longValue();
        Long output_2 = input_2_0.longValue();

        
        // Compare output
        if (output_1 == 23L && output_2 == -11740090L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

