

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Byte output_1 = input_1_0.byteValue();
        Byte output_2 = input_2_0.byteValue();

        
        // Compare output
        if (output_1 == -1 && output_2 == 19) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

