

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toString(input_1_0);
        String output_2 = Double.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("2.7567850011919407E125") && output_2.equals("8.134464836499207E-85")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

