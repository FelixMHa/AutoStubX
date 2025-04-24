

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_1_1 = Short.valueOf(args[1]);
        Short input_2_0 = Short.valueOf(args[2]);
        Short input_2_1 = Short.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = Short.compareUnsigned(input_1_0, input_1_1);
        Integer output_2 = Short.compareUnsigned(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == -65506 && output_2 == 65024) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

