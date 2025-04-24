

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = String.valueOf(input_1_0);
        String output_2 = String.valueOf(input_2_0);

        
        // Compare output
        if (output_1.equals("-3.9349828638128525E152") && output_2.equals("4.98266325206737E114")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

