

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = String.valueOf(input_1_0);
        String output_2 = String.valueOf(input_2_0);

        
        // Compare output
        if (output_1.equals("-1.0320756700749937E-105") && output_2.equals("1.0170834849170963E40")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

