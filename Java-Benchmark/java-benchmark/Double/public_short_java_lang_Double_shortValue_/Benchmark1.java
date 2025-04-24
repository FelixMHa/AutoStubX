

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Short output_1 = input_1_0.shortValue();
        Short output_2 = input_2_0.shortValue();

        
        // Compare output
        if (output_1 == 0 && output_2 == -1) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

