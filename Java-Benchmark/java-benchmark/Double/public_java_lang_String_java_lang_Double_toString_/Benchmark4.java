

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("-1.0111665402719284E15") && output_2.equals("1.8221691363321281E-34")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

