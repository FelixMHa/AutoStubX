

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        Integer input_2_0 = Integer.valueOf(args[2]);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        Long output_1 = Math.multiplyFull(input_1_0, input_1_1);
        Long output_2 = Math.multiplyFull(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == 25545L && output_2 == 0L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

