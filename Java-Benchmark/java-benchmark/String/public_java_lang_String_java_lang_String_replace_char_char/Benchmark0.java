

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        Character input_1_1 = args[1].charAt(0);
        Character input_1_2 = args[2].charAt(0);
        String input_2_0 = String.valueOf(args[3]);
        Character input_2_1 = args[4].charAt(0);
        Character input_2_2 = args[5].charAt(0);


        // Perform computation         
        String output_1 = input_1_0.replace(input_1_1, input_1_2);
        String output_2 = input_2_0.replace(input_2_1, input_2_2);

        
        // Compare output
        if (output_1.equals("") && output_2.equals("CU")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

