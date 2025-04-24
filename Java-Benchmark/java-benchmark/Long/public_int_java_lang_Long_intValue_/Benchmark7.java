

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.intValue();
        Integer output_2 = input_2_0.intValue();

        
        // Compare output
        if (output_1 == -3638019 && output_2 == 1929520070) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

