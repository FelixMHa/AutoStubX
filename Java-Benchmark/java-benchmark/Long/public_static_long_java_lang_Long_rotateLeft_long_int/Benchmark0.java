

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        Long input_2_0 = Long.valueOf(args[2]);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        Long output_1 = Long.rotateLeft(input_1_0, input_1_1);
        Long output_2 = Long.rotateLeft(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == -216505669011111L && output_2 == -8818857315155872406L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

