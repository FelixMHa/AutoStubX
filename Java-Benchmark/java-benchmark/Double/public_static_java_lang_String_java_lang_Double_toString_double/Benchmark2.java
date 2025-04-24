

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toString(input_1_0);
        String output_2 = Double.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("-3.0244548934761986E-95") && output_2.equals("3.1222655227610702E-142")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

