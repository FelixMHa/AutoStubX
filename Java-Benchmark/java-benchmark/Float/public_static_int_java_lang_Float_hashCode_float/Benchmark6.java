

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Float.hashCode(input_1_0);
        Integer output_2 = Float.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 1646688044 && output_2 == -825721312) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

