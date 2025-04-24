

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Byte output_1 = input_1_0.byteValue();
        Byte output_2 = input_2_0.byteValue();

        
        // Compare output
        if (output_1 == 93 && output_2 == -41) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

