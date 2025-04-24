

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Long output_1 = input_1_0.longValue();
        Long output_2 = input_2_0.longValue();

        
        // Compare output
        if (output_1 == 44164L && output_2 == -251L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

