

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        Long input_1_1 = Long.valueOf(args[1]);
        String input_2_0 = String.valueOf(args[2]);
        Long input_2_1 = Long.valueOf(args[3]);


        // Perform computation         
        Long output_1 = Long.getLong(input_1_0, input_1_1);
        Long output_2 = Long.getLong(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == 95421L && output_2 == -3978L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

