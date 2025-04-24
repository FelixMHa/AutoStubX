

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Short.toUnsignedLong(input_1_0);
        Long output_2 = Short.toUnsignedLong(input_2_0);

        
        // Compare output
        if (output_1 == 58L && output_2 == 584L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

