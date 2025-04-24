

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        Long input_2_0 = Long.valueOf(args[2]);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        String output_1 = Long.toUnsignedString(input_1_0, input_1_1);
        String output_2 = Long.toUnsignedString(input_2_0, input_2_1);

        
        // Compare output
        if (output_1.equals("18446743597692638092") && output_2.equals("18438683046063945811")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

