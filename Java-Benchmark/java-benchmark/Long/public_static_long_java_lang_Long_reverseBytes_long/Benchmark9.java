

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Long.reverseBytes(input_1_0);
        Long output_2 = Long.reverseBytes(input_2_0);

        
        // Compare output
        if (output_1 == 128L && output_2 == 2660775418118144000L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

