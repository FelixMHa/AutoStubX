

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Double output_1 = input_1_0.doubleValue();
        Double output_2 = input_2_0.doubleValue();

        
        // Compare output
        if (output_1 == -17.0 && output_2 == -5.0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

