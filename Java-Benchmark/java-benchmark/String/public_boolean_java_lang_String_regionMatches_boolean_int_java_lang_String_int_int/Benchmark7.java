

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        Boolean input_1_1 = Boolean.valueOf(args[1]);
        Integer input_1_2 = Integer.valueOf(args[2]);
        String input_1_3 = String.valueOf(args[3]);
        Integer input_1_4 = Integer.valueOf(args[4]);
        Integer input_1_5 = Integer.valueOf(args[5]);
        String input_2_0 = String.valueOf(args[6]);
        Boolean input_2_1 = Boolean.valueOf(args[7]);
        Integer input_2_2 = Integer.valueOf(args[8]);
        String input_2_3 = String.valueOf(args[9]);
        Integer input_2_4 = Integer.valueOf(args[10]);
        Integer input_2_5 = Integer.valueOf(args[11]);


        // Perform computation         
        Boolean output_1 = input_1_0.regionMatches(input_1_1, input_1_2, input_1_3, input_1_4, input_1_5);
        Boolean output_2 = input_2_0.regionMatches(input_2_1, input_2_2, input_2_3, input_2_4, input_2_5);

        
        // Compare output
        if (output_1 == false && output_2 == true) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

