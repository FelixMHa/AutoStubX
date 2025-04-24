

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Float input_1_0 = Float.valueOf(args[0]);
        Float input_2_0 = Float.valueOf(args[1]);


        // Perform computation         
        String output_1 = Float.toHexString(input_1_0);
        String output_2 = Float.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("0x1.d6aee8p-24") && output_2.equals("0x1.9d7d78p-11")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

