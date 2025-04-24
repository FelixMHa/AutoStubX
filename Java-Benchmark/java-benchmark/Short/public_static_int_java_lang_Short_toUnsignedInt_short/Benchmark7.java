

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Short.toUnsignedInt(input_1_0);
        Integer output_2 = Short.toUnsignedInt(input_2_0);

        
        // Compare output
        if (output_1 == 49528 && output_2 == 73) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

