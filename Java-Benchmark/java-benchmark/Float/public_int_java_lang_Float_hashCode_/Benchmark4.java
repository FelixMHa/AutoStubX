

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.hashCode();
        Integer output_2 = input_2_0.hashCode();

        
        // Compare output
        if (output_1 == -1359622072 && output_2 == 737024896) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

