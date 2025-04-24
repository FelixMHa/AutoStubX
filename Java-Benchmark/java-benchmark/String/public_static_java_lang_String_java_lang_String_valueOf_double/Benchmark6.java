

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = String.valueOf(input_1_0);
        String output_2 = String.valueOf(input_2_0);

        
        // Compare output
        if (output_1.equals("1.4827774923239025E-79") && output_2.equals("1.7931123495075924E117")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

