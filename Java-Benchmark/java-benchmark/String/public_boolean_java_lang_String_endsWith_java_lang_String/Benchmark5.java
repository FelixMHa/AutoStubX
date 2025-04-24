

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        String input_1_1 = String.valueOf(args[1]);
        String input_2_0 = String.valueOf(args[2]);
        String input_2_1 = String.valueOf(args[3]);


        // Perform computation         
        Boolean output_1 = input_1_0.endsWith(input_1_1);
        Boolean output_2 = input_2_0.endsWith(input_2_1);

        
        // Compare output
        if (output_1 == true && output_2 == false) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

