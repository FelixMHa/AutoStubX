

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_1_1 = Short.valueOf(args[1]);
        Short input_2_0 = Short.valueOf(args[2]);
        Short input_2_1 = Short.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = Short.compare(input_1_0, input_1_1);
        Integer output_2 = Short.compare(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == -3142 && output_2 == 3488) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

