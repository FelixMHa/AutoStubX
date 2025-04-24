

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Byte output_1 = input_1_0.byteValue();
        Byte output_2 = input_2_0.byteValue();

        
        // Compare output
        if (output_1 == 0 && output_2 == 60) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

