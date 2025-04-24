

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        String output_1 = Double.toHexString(input_1_0);
        String output_2 = Double.toHexString(input_2_0);

        
        // Compare output
        if (output_1.equals("-0x1.46e47da7dfd5dp414") && output_2.equals("0x1.1ebf9feb54034p-486")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

