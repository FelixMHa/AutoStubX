

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.hashCode();
        Integer output_2 = input_2_0.hashCode();

        
        // Compare output
        if (output_1 == 227400602 && output_2 == 1428662168) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

