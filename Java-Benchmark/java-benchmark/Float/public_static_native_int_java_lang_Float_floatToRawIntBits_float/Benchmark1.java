

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Float.floatToRawIntBits(input_1_0);
        Integer output_2 = Float.floatToRawIntBits(input_2_0);

        
        // Compare output
        if (output_1 == -170195724 && output_2 == 2026805119) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

