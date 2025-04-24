

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = String.valueOf(input_1_0);
        String output_2 = String.valueOf(input_2_0);

        
        // Compare output
        if (output_1.equals("1399071091772363") && output_2.equals("41")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

