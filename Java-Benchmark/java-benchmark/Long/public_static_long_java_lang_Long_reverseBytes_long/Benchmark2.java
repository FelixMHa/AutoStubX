

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Long.reverseBytes(input_1_0);
        Long output_2 = Long.reverseBytes(input_2_0);

        
        // Compare output
        if (output_1 == -1723159021097058304L && output_2 == -7154359397383130880L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

