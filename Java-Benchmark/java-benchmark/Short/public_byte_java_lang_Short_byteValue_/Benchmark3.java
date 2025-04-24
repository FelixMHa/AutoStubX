

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Byte output_1 = input_1_0.byteValue();
        Byte output_2 = input_2_0.byteValue();

        
        // Compare output
        if (output_1 == -1 && output_2 == -3) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

