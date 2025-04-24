

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = Float.toHexString(input_1_0);
        String output_2 = Float.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("0x1.7bbf5p-91") && output_2.equals("0x1.4aaf88p-104")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

