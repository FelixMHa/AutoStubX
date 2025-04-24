

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Double.doubleToRawLongBits(input_1_0);
        Long output_2 = Double.doubleToRawLongBits(input_2_0);

        
        // Compare output
        if (output_1 == -3780778915920675614L && output_2 == 2882110266702125810L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

