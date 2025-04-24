

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Float.floatToRawIntBits(input_1_0);
        Integer output_2 = Float.floatToRawIntBits(input_2_0);

        
        // Compare output
        if (output_1 == -1494959796 && output_2 == -2102370744) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

