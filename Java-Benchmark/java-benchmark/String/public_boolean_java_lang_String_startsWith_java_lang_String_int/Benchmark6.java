

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        String input_1_1 = String.valueOf(args[1]);
        Integer input_1_2 = Integer.valueOf(args[2]);
        String input_2_0 = String.valueOf(args[3]);
        String input_2_1 = String.valueOf(args[4]);
        Integer input_2_2 = Integer.valueOf(args[5]);


        // Perform computation         
        Boolean output_1 = input_1_0.startsWith(input_1_1, input_1_2);
        Boolean output_2 = input_2_0.startsWith(input_2_1, input_2_2);

        
        // Compare output
        if (output_1 == false && output_2 == true) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

