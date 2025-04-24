

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Float output_1 = input_1_0.floatValue();
        Float output_2 = input_2_0.floatValue();

        
        // Compare output
        if (output_1 == 216618467000.0 && output_2 == -4196479010000.0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

