

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("-3.3799630321101215E70") && output_2.equals("-6.293307134940173E-90")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

