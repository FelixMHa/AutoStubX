

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Byte output_1 = Byte.valueOf(input_1_0);
        Byte output_2 = Byte.valueOf(input_2_0);

        
        // Compare output
        if (output_1 == -25 && output_2 == 9) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

