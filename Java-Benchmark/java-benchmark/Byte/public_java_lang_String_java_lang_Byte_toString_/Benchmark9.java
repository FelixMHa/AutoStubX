

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("-7") && output_2.equals("0")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

