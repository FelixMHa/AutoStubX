

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Float output_1 = input_1_0.floatValue();
        Float output_2 = input_2_0.floatValue();

        
        // Compare output
        if (output_1 == -9.0 && output_2 == 1.0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

