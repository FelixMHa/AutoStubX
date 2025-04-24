

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        String input_2_0 = String.valueOf(args[1]);


        // Perform computation         
        Boolean output_1 = input_1_0.isEmpty();
        Boolean output_2 = input_2_0.isEmpty();

        
        // Compare output
        if (output_1 == true && output_2 == false) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

