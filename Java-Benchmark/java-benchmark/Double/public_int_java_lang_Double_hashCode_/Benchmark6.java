

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.hashCode();
        Integer output_2 = input_2_0.hashCode();

        
        // Compare output
        if (output_1 == 28572334 && output_2 == -1996008008) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

