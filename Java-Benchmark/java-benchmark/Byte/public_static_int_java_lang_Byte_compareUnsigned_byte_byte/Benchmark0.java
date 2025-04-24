

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_1_1 = Byte.valueOf(args[1]);
        Byte input_2_0 = Byte.valueOf(args[2]);
        Byte input_2_1 = Byte.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = Byte.compareUnsigned(input_1_0, input_1_1);
        Integer output_2 = Byte.compareUnsigned(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == 226 && output_2 == 3) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

