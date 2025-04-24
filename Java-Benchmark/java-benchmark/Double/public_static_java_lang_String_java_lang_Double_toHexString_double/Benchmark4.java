

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toHexString(input_1_0);
        String output_2 = Double.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("-0x1.22960b18facc8p-487") && output_2.equals("-0x1.5022ca58b695ep-506")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

