

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Boolean input_1_0 = Boolean.valueOf(args[0]);
        Boolean input_2_0 = Boolean.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Boolean.hashCode(input_1_0);
        Integer output_2 = Boolean.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 1237 && output_2 == 1231) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

