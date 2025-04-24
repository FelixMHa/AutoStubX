

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        String input_1_2 = String.valueOf(args[2]);
        Integer input_1_3 = Integer.valueOf(args[3]);
        Integer input_1_4 = Integer.valueOf(args[4]);
        String input_2_0 = String.valueOf(args[5]);
        Integer input_2_1 = Integer.valueOf(args[6]);
        String input_2_2 = String.valueOf(args[7]);
        Integer input_2_3 = Integer.valueOf(args[8]);
        Integer input_2_4 = Integer.valueOf(args[9]);


        // Perform computation         
        Boolean output_1 = input_1_0.regionMatches(input_1_1, input_1_2, input_1_3, input_1_4);
        Boolean output_2 = input_2_0.regionMatches(input_2_1, input_2_2, input_2_3, input_2_4);

        
        // Compare output
        if (output_1 == false && output_2 == true) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

