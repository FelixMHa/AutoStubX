

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        String input_2_0 = String.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.hashCode();
        Integer output_2 = input_2_0.hashCode();

        
        // Compare output
        if (output_1 == 0 && output_2 == 1366931) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

