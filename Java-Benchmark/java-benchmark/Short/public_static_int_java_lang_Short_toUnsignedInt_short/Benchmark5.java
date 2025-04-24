

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Short.toUnsignedInt(input_1_0);
        Integer output_2 = Short.toUnsignedInt(input_2_0);

        
        // Compare output
        if (output_1 == 0 && output_2 == 6498) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

