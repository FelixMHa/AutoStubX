

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        Integer input_2_0 = Integer.valueOf(args[2]);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = Math.min(input_1_0, input_1_1);
        Integer output_2 = Math.min(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == -381 && output_2 == -465406) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

