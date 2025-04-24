

public class Benchmark2 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = Float.toHexString(input_1_0);
        String output_2 = Float.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("0x1.0abb34p-25") && output_2.equals("0x1.f52598p-103")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

