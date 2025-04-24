

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Float output_1 = input_1_0.floatValue();
        Float output_2 = input_2_0.floatValue();

        
        // Compare output
        if (output_1 == 121.0 && output_2 == -13.0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

