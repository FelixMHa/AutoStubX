

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Double.doubleToLongBits(input_1_0);
        Long output_2 = Double.doubleToLongBits(input_2_0);

        
        // Compare output
        if (output_1 == 3168488079502624568L && output_2 == 3267893786809332632L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

