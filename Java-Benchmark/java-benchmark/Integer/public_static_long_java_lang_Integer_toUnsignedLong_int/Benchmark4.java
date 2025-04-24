

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Integer.toUnsignedLong(input_1_0);
        Long output_2 = Integer.toUnsignedLong(input_2_0);

        
        // Compare output
        if (output_1 == 4291652816L && output_2 == 4294965668L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

