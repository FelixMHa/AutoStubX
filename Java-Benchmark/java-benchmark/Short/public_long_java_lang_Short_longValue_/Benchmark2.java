

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Long output_1 = input_1_0.longValue();
        Long output_2 = input_2_0.longValue();

        
        // Compare output
        if (output_1 == 0L && output_2 == 16L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

