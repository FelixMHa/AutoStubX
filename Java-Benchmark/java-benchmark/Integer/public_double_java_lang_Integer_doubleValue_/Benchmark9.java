

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Double output_1 = input_1_0.doubleValue();
        Double output_2 = input_2_0.doubleValue();

        
        // Compare output
        if (output_1 == -96.0 && output_2 == -2688905.0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

