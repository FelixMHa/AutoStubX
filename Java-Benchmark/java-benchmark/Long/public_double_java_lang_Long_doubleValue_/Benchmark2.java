

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Double output_1 = input_1_0.doubleValue();
        Double output_2 = input_2_0.doubleValue();

        
        // Compare output
        if (output_1 == -4048795342267.0 && output_2 == 1348.0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

