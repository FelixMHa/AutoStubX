

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Long output_1 = input_1_0.longValue();
        Long output_2 = input_2_0.longValue();

        
        // Compare output
        if (output_1 == 0L && output_2 == -1L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

