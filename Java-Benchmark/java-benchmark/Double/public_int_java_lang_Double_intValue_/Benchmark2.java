

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.intValue();
        Integer output_2 = input_2_0.intValue();

        
        // Compare output
        if (output_1 == 1 && output_2 == 2147483647) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

