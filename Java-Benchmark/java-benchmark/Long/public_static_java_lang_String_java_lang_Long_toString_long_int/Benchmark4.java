

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        Long input_2_0 = Long.valueOf(args[2]);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        String output_1 = Long.toString(input_1_0, input_1_1);
        String output_2 = Long.toString(input_2_0, input_2_1);

        
        // Compare output
        if (output_1.equals("-88164699") && output_2.equals("3hk6lf6k")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

