

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toString(input_1_0);
        String output_2 = Double.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("2.4319744422471424E152") && output_2.equals("1.3270318133390554E-130")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

