

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Byte output_1 = Byte.valueOf(input_1_0);
        Byte output_2 = Byte.valueOf(input_2_0);

        
        // Compare output
        if (output_1 == 9 && output_2 == 30) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

