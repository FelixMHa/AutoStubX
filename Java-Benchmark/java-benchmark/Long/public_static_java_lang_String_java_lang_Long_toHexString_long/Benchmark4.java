

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toHexString(input_1_0);
        String output_2 = Long.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("fff9581764a1b33d") && output_2.equals("9bd769514d157")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

