

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Byte.toUnsignedLong(input_1_0);
        Long output_2 = Byte.toUnsignedLong(input_2_0);

        
        // Compare output
        if (output_1 == 244L && output_2 == 241L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

