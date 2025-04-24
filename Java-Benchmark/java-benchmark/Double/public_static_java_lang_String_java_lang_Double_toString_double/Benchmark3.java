

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toString(input_1_0);
        String output_2 = Double.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("-1.565231052740366E111") && output_2.equals("-9.037582804970355E-97")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

