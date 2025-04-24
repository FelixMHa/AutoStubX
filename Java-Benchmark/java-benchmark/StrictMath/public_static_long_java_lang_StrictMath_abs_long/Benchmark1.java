

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = StrictMath.abs(input_1_0);
        Long output_2 = StrictMath.abs(input_2_0);

        
        // Compare output
        if (output_1 == 7570318L && output_2 == 1068292794L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

