

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Byte.toUnsignedInt(input_1_0);
        Integer output_2 = Byte.toUnsignedInt(input_2_0);

        
        // Compare output
        if (output_1 == 199 && output_2 == 26) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

