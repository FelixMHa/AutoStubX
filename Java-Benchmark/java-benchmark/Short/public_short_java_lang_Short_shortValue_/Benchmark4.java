

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Short output_1 = input_1_0.shortValue();
        Short output_2 = input_2_0.shortValue();

        
        // Compare output
        if (output_1 == -755 && output_2 == -32768) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

