

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.intValue();
        Integer output_2 = input_2_0.intValue();

        
        // Compare output
        if (output_1 == -3 && output_2 == -53) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

