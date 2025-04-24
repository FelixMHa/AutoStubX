

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toHexString(input_1_0);
        String output_2 = Long.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("1975400") && output_2.equals("ff0ec53ad2afcc14")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

