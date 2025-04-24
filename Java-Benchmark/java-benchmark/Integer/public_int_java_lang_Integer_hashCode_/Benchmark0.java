

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.hashCode();
        Integer output_2 = input_2_0.hashCode();

        
        // Compare output
        if (output_1 == -108655176 && output_2 == 0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

