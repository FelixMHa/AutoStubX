

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        Integer input_2_0 = Integer.valueOf(args[2]);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        String output_1 = Integer.toString(input_1_0, input_1_1);
        String output_2 = Integer.toString(input_2_0, input_2_1);

        
        // Compare output
        if (output_1.equals("-945145621") && output_2.equals("1")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

