

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Character.toTitleCase(input_1_0);
        Integer output_2 = Character.toTitleCase(input_2_0);

        
        // Compare output
        if (output_1 == -248 && output_2 == -478) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

