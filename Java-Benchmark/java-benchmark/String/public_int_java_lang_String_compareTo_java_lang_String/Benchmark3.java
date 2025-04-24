

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        String input_1_1 = String.valueOf(args[1]);
        String input_2_0 = String.valueOf(args[2]);
        String input_2_1 = String.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = input_1_0.compareTo(input_1_1);
        Integer output_2 = input_2_0.compareTo(input_2_1);

        
        // Compare output
        if (output_1 == 0 && output_2 == 2) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

