

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Integer input_1_1 = Integer.valueOf(args[1]);
        Character input_2_0 = args[2].charAt(0);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = Character.digit(input_1_0, input_1_1);
        Integer output_2 = Character.digit(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == -1 && output_2 == 9) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

