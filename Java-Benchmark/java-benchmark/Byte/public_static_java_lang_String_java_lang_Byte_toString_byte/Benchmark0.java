

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        String output_1 = Byte.toString(input_1_0);
        String output_2 = Byte.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("5") && output_2.equals("3")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

