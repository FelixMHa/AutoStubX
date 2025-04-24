

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.intValue();
        Integer output_2 = input_2_0.intValue();

        
        // Compare output
        if (output_1 == -207023 && output_2 == 322342506) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

