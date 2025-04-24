

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Double.doubleToLongBits(input_1_0);
        Long output_2 = Double.doubleToLongBits(input_2_0);

        
        // Compare output
        if (output_1 == -5993670162077983568L && output_2 == 3444871647990083772L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

