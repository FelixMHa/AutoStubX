

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("1.573762218941311E-75") && output_2.equals("3.949598907621078E-27")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

