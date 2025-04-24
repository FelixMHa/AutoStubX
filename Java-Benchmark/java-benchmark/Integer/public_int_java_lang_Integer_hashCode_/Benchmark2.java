

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.hashCode();
        Integer output_2 = input_2_0.hashCode();

        
        // Compare output
        if (output_1 == 4426168 && output_2 == 220209) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

