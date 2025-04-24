

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Character.toTitleCase(input_1_0);
        Integer output_2 = Character.toTitleCase(input_2_0);

        
        // Compare output
        if (output_1 == -33976217 && output_2 == -3807082) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

