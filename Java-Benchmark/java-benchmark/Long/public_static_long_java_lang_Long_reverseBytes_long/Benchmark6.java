

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Long.reverseBytes(input_1_0);
        Long output_2 = Long.reverseBytes(input_2_0);

        
        // Compare output
        if (output_1 == 1636636385255048952L && output_2 == -6048496997214715904L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

