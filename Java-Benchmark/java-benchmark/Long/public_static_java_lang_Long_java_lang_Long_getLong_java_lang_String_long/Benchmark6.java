

public class Benchmark6 {
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
        if (output_1 == -268727691516210980L && output_2 == 10875L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

