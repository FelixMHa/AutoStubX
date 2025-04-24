

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Boolean input_1_0 = Boolean.valueOf(args[0]);
        Boolean input_2_0 = Boolean.valueOf(args[1]);


        // Perform computation         
        Boolean output_1 = input_1_0.booleanValue();
        Boolean output_2 = input_2_0.booleanValue();

        
        // Compare output
        if (output_1 == false && output_2 == true) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

