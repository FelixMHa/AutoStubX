

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Short output_1 = input_1_0.shortValue();
        Short output_2 = input_2_0.shortValue();

        
        // Compare output
        if (output_1 == -7 && output_2 == -102) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

