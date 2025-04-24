

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Short output_1 = Short.reverseBytes(input_1_0);
        Short output_2 = Short.reverseBytes(input_2_0);

        
        // Compare output
        if (output_1 == 27392 && output_2 == 14336) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

