

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        Integer input_2_0 = Integer.valueOf(args[2]);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = input_1_0.compareTo(input_1_1);
        Integer output_2 = input_2_0.compareTo(input_2_1);

        
        // Compare output
        if (output_1 == -1 && output_2 == 1) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

