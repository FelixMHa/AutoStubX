

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Integer.hashCode(input_1_0);
        Integer output_2 = Integer.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 1441 && output_2 == -2643372) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

