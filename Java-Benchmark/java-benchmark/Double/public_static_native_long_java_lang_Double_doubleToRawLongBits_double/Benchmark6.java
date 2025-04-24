

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Double.doubleToRawLongBits(input_1_0);
        Long output_2 = Double.doubleToRawLongBits(input_2_0);

        
        // Compare output
        if (output_1 == 5843934678780892621L && output_2 == 4744995236645501350L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

