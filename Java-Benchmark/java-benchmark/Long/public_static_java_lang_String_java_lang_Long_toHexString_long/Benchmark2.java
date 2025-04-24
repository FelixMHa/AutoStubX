

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toHexString(input_1_0);
        String output_2 = Long.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("442954e5") && output_2.equals("3e46b")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

