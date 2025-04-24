

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        String output_1 = Integer.toHexString(input_1_0);
        String output_2 = Integer.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("a8c92d73") && output_2.equals("1fdf")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

